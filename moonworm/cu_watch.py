import json
import logging
import os
import pprint as pp
import re
import time
from os import stat
from re import S
from typing import Any, Dict, List, Optional, cast

import web3
from eth_typing.evm import ChecksumAddress
from moonstreamdb.db import yield_db_session_ctx
from moonstreamdb.models import EthereumLabel, PolygonLabel
from sqlalchemy.orm import Query, Session
from sqlalchemy.sql.expression import delete
from tqdm import tqdm
from web3 import Web3
from web3.middleware import geth_poa_middleware

from moonworm.crawler.moonstream_ethereum_state_provider import (
    MoonstreamEthereumStateProvider,
)
from moonworm.crawler.networks import Network

from .contracts import CU, ERC721
from .crawler.ethereum_state_provider import EthereumStateProvider
from .crawler.function_call_crawler import (
    ContractFunctionCall,
    FunctionCallCrawler,
    FunctionCallCrawlerState,
    Web3StateProvider,
    utfy_dict,
)
from .crawler.log_scanner import _fetch_events_chunk

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _get_last_crawled_block(
    session: Session, contract_address: ChecksumAddress
) -> Optional[int]:
    """
    Gets the last block that was crawled.
    """

    query = (
        session.query(PolygonLabel)
        .filter(
            PolygonLabel.label == "moonworm",
            PolygonLabel.address == contract_address,
        )
        .order_by(PolygonLabel.block_number.desc())
    )
    if query.count():
        return query.first().block_number
    return None


def _add_function_call_labels(
    session: Session,
    function_calls: List[ContractFunctionCall],
    address: ChecksumAddress,
) -> None:
    """
    Adds a label to a function call.
    """

    existing_function_call_labels = (
        session.query(PolygonLabel)
        .filter(
            PolygonLabel.label == "moonworm",
            PolygonLabel.log_index == None,
            PolygonLabel.address == address,
            PolygonLabel.transaction_hash.in_(
                [call.transaction_hash for call in function_calls]
            ),
        )
        .all()
    )
    # deletin existing labels
    for label in existing_function_call_labels:
        session.delete(label)

    try:
        if existing_function_call_labels:
            logger.info(
                f"Deleting {len(existing_function_call_labels)} existing tx labels"
            )
            session.commit()
    except Exception as e:
        try:
            session.commit()
        except:
            logger.error(f"Failed!!!\n{e}")
            session.rollback()

    for function_call in function_calls:
        label = PolygonLabel(
            label="moonworm",
            label_data={
                "type": "tx_call",
                "name": function_call.function_name,
                "caller": function_call.caller_address,
                "args": function_call.function_args,
                "status": function_call.status,
                "gasUsed": function_call.gas_used,
            },
            address=function_call.contract_address,
            block_number=function_call.block_number,
            transaction_hash=function_call.transaction_hash,
            block_timestamp=function_call.block_timestamp,
        )
        session.add(label)
    try:
        session.commit()
    except Exception as e:
        try:
            session.commit()
        except:
            logger.error(f"Failed!!!\n{e}")
            session.rollback()


def _add_event_labels(
    session: Session, events: List[Dict[str, Any]], address: ChecksumAddress
) -> None:
    """
    Adds events to database.
    """

    transactions = [event["transactionHash"] for event in events]
    log_indexes = [event["logIndex"] for event in events]
    for ev in events:
        print(ev)
    existing_event_labels = (
        session.query(PolygonLabel)
        .filter(
            PolygonLabel.label == "moonworm",
            PolygonLabel.address == address,
            PolygonLabel.transaction_hash.in_(transactions),
            PolygonLabel.log_index != None,
        )
        .all()
    )

    # deletin existing labels
    deleted = 0
    for label in existing_event_labels:
        if label.log_index in log_indexes:
            deleted += 1
            session.delete(label)

    try:
        if deleted > 0:
            logger.error(f"Deleting {deleted} existing event labels")
            session.commit()
    except Exception as e:
        try:
            session.commit()
        except:
            logger.error(f"Failed!!!\n{e}")
            session.rollback()

    for event in events:
        label = PolygonLabel(
            label="moonworm",
            label_data={
                "type": "event",
                "name": event["event"],
                "args": event["args"],
            },
            address=event["address"],
            block_number=event["blockNumber"],
            transaction_hash=event["transactionHash"],
            block_timestamp=event["blockTimestamp"],
            log_index=event["logIndex"],
        )
        session.add(label)
    try:
        session.commit()
    except Exception as e:
        try:
            session.commit()
        except:
            logger.error(f"Failed!!!\n{e}")
            session.rollback()


class MockState(FunctionCallCrawlerState):
    def __init__(self) -> None:
        self.state: List[ContractFunctionCall] = []

    def get_last_crawled_block(self) -> int:
        """
        Returns the last block number that was crawled.
        """
        return 0

    def register_call(self, function_call: ContractFunctionCall) -> None:
        """
        Processes the given function call (store it, etc.).
        """
        self.state.append(function_call)

    def flush(self) -> None:
        """
        Flushes cached state to storage layer.
        """
        self.state = []


WEB3_PROVIDER_URL_1 = os.environ.get("WEB3_PROVIDER_URL_1", "")
WEB3_PROVIDER_URL_2 = os.environ.get("WEB3_PROVIDER_URL_2", "")
WEB3_PROVIDER_URL_3 = os.environ.get("WEB3_PROVIDER_URL_3", "")
if WEB3_PROVIDER_URL_1 == "" or WEB3_PROVIDER_URL_2 == "" or WEB3_PROVIDER_URL_3 == "":
    raise ValueError(
        "Please set WEB3_PROVIDER_URL_1, WEB3_PROVIDER_URL_2, WEB3_PROVIDER_URL_3"
    )

WEB3_PROVIDER_URLS = [
    WEB3_PROVIDER_URL_1,
    WEB3_PROVIDER_URL_2,
    WEB3_PROVIDER_URL_3,
]
CURR_INDEX = 0


def get_web3_client():
    global CURR_INDEX
    CURR_INDEX = (CURR_INDEX + 1) % len(WEB3_PROVIDER_URLS)
    web3 = Web3(Web3.HTTPProvider(WEB3_PROVIDER_URLS[CURR_INDEX]))
    web3.middleware_onion.inject(geth_poa_middleware, layer=0)
    return web3


def watch_cu_contract(
    web3: Web3,
    contract_address: ChecksumAddress,
    contract_abi: List[Dict[str, Any]],
    num_confirmations: int = 60,
    min_blocks_to_crawl: int = 10,
    sleep_time: float = 1,
    start_block: Optional[int] = None,
    force_start: bool = False,
    use_moonstream_web3_provider: bool = False,
) -> None:
    """
    Watches a contract for events and calls.
    """
    if force_start and start_block is None:
        raise ValueError("start_block must be specified if force_start is True")

    with yield_db_session_ctx() as session:
        function_call_state = MockState()

        eth_state_provider: Optional[EthereumStateProvider] = None
        if use_moonstream_web3_provider:
            eth_state_provider = MoonstreamEthereumStateProvider(
                web3, network=Network.polygon, db_session=session
            )
        else:
            eth_state_provider = Web3StateProvider(web3)

        crawler = FunctionCallCrawler(
            function_call_state,
            eth_state_provider,
            contract_abi,
            [web3.toChecksumAddress(contract_address)],
        )

        last_crawled_block = _get_last_crawled_block(session, contract_address)
        if start_block is None:
            if last_crawled_block is not None:
                current_block = last_crawled_block
                logger.info(f"Starting from block {current_block}, last crawled block")
            else:
                current_block = web3.eth.blockNumber - num_confirmations * 2
                logger.info(f"Starting from block {current_block}, current block")
        else:
            current_block = start_block
            if not force_start and last_crawled_block is not None:
                if start_block > last_crawled_block:
                    logger.info(
                        f"Starting from block {start_block}, last crawled block {last_crawled_block}"
                    )
                else:
                    current_block = last_crawled_block
                    logger.info(f"Starting from last crawled block {current_block}")

        event_abis = [item for item in contract_abi if item["type"] == "event"]

        while True:
            try:
                web3 = get_web3_client()
                session.execute("select 1")
                time.sleep(sleep_time)
                end_block = min(
                    web3.eth.blockNumber - num_confirmations, current_block + 100
                )
                if end_block < current_block + min_blocks_to_crawl:
                    logger.info(
                        f"Sleeping crawling, end_block {end_block} < current_block {current_block} + min_blocks_to_crawl {min_blocks_to_crawl}"
                    )
                    sleep_time += 1
                    continue

                sleep_time /= 2

                logger.info("Getting txs")
                crawler.crawl(current_block, end_block)
                if function_call_state.state:
                    _add_function_call_labels(
                        session, function_call_state.state, contract_address
                    )
                    logger.info(
                        f"Got  {len(function_call_state.state)} transaction calls:"
                    )
                    function_call_state.flush()

                logger.info("Getting events")
                all_events = []
                for event_abi in event_abis:
                    raw_events = _fetch_events_chunk(
                        web3,
                        event_abi,
                        current_block,
                        end_block,
                        [contract_address],
                    )

                    for raw_event in raw_events:
                        raw_event["blockTimestamp"] = (
                            crawler.ethereum_state_provider.get_block_timestamp(
                                raw_event["blockNumber"]
                            ),
                        )
                        all_events.append(raw_event)

                if all_events:
                    print(f"Got {len(all_events)} events:")
                    _add_event_labels(session, all_events, contract_address)
                logger.info(f"Current block {end_block + 1}")
                current_block = end_block + 1
            except Exception as e:
                logger.error(f"Something went wrong: {e}")
                web3 = get_web3_client()
                logger.info(f"Trying to recover from error")
                for i in range(10):
                    logger.info(f"Attempt {i}:")
                    try:
                        time.sleep(10)
                        logger.info("Trying to reconnect to database")
                        session.rollback()
                        session.execute("select 1")
                        logger.info("Trying to reconnect to web3")
                        web3.eth.block_number
                        break
                    except Exception as e:
                        logger.error(f"Failed: {e}")
                        continue

                try:
                    session.execute("select 1")
                    web3.eth.block_number
                    continue
                except Exception as e:
                    logger.error("Moonworm is going to die")
                    raise e

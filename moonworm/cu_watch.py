import pprint as pp
from re import S
import time
from typing import Any, Dict, List, Optional, cast
import json

import web3
from eth_typing.evm import ChecksumAddress
from tqdm import tqdm
from web3 import Web3

from moonstreamdb.models import PolygonLabel

from .contracts import CU, ERC721
from .crawler.function_call_crawler import (
    ContractFunctionCall,
    FunctionCallCrawler,
    FunctionCallCrawlerState,
    Web3StateProvider,
)
from .crawler.log_scanner import _fetch_events_chunk

from sqlalchemy.orm import Query, Session


def _add_function_call_labels(
    session: Session,
    function_calls: List[ContractFunctionCall],
) -> None:
    """
    Adds a label to a function call.
    """
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
        print("Committing tx_call labels to database...")
        session.commit()
    except Exception as e:
        print(f"Failed!!!\n{e}")
        session.rollback()


def _add_event_labels(session: Session, events: List[Dict[str, Any]]) -> None:
    """
    Adds events to database.
    """
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
        print("Committing event labels to database...")
        session.commit()
    except Exception as e:
        print(f"Failed!!!\n{e}")
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


def watch_cu_contract(
    session: Session,
    web3: Web3,
    contract_address: ChecksumAddress,
    contract_abi: List[Dict[str, Any]],
    num_confirmations: int = 10,
    sleep_time: float = 1,
    start_block: Optional[int] = None,
) -> None:
    """
    Watches a contract for events and calls.
    """
    state = MockState()
    crawler = FunctionCallCrawler(
        state,
        Web3StateProvider(web3),
        contract_abi,
        [web3.toChecksumAddress(contract_address)],
    )

    event_abis = [item for item in contract_abi if item["type"] == "event"]

    if start_block is None:
        current_block = web3.eth.blockNumber - num_confirmations * 2
    else:
        current_block = start_block

    progress_bar = tqdm(unit=" blocks")
    progress_bar.set_description(f"Current block {current_block}")
    while True:
        time.sleep(sleep_time)
        end_block = min(web3.eth.blockNumber - num_confirmations, current_block + 100)
        if end_block < current_block:
            sleep_time *= 2
            continue

        sleep_time /= 2

        crawler.crawl(current_block, end_block)
        if state.state:
            _add_function_call_labels(session, state.state)
            print("Got transaction calls:")
            for call in state.state:
                pp.pprint(call, width=200, indent=4)
            state.flush()

        for event_abi in event_abis:
            raw_events = _fetch_events_chunk(
                web3,
                event_abi,
                current_block,
                end_block,
                [contract_address],
            )
            all_events = []
            for raw_event in raw_events:
                print("Got event:")
                event = {
                    "event": raw_event["event"],
                    "args": json.loads(Web3.toJSON(raw_event["args"])),
                    "address": raw_event["address"],
                    "blockNumber": raw_event["blockNumber"],
                    "transactionHash": raw_event["transactionHash"].hex(),
                    "blockTimestamp": crawler.ethereum_state_provider.get_block_timestamp(
                        raw_event["blockNumber"]
                    ),
                    "logIndex": raw_event["logIndex"],
                }
                all_events.append(event)
                pp.pprint(event, width=200, indent=4)

            if all_events:
                _add_event_labels(session, all_events)

        progress_bar.set_description(
            f"Current block {end_block + 1}, Already watching for"
        )
        progress_bar.update(end_block - current_block + 1)
        current_block = end_block + 1

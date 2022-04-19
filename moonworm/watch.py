import json
import pprint as pp
import time
from dataclasses import asdict
from typing import Any, Dict, List, Optional, Tuple

from eth_typing.evm import ChecksumAddress
from tqdm import tqdm
from web3 import Web3

from moonworm.crawler.ethereum_state_provider import EthereumStateProvider

from .contracts import CU, ERC721
from .crawler.function_call_crawler import (
    ContractFunctionCall,
    FunctionCallCrawler,
    FunctionCallCrawlerState,
    Web3StateProvider,
)
from .crawler.log_scanner import _fetch_events_chunk


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


# TODO(yhtiyar), use state_provider.get_last_block
def watch_contract(
    web3: Web3,
    state_provider: EthereumStateProvider,
    contract_address: ChecksumAddress,
    contract_abi: List[Dict[str, Any]],
    num_confirmations: int = 10,
    sleep_time: float = 1,
    start_block: Optional[int] = None,
    end_block: Optional[int] = None,
    min_blocks_batch: int = 100,
    max_blocks_batch: int = 5000,
    batch_size_update_threshold: int = 100,
    only_events: bool = False,
    outfile: Optional[str] = None,
) -> None:
    """
    Watches a contract for events and calls.
    """

    def _crawl_events(
        event_abi, from_block: int, to_block: int, batch_size: int
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Crawls events from the given block range.
        reduces the batch_size if response is failing.
        increases the batch_size if response is successful.
        """
        events = []
        current_from_block = from_block

        while current_from_block <= to_block:
            current_to_block = min(current_from_block + batch_size, to_block)
            try:
                events_chunk = _fetch_events_chunk(
                    web3,
                    event_abi,
                    current_from_block,
                    current_to_block,
                    [contract_address],
                )
                events.extend(events_chunk)
                current_from_block = current_to_block + 1
                if len(events) <= batch_size_update_threshold:
                    batch_size = min(batch_size * 2, max_blocks_batch)
            except Exception as e:
                if batch_size <= min_blocks_batch:
                    raise e
                time.sleep(0.1)
                batch_size = max(batch_size // 2, min_blocks_batch)
        return events, batch_size

    current_batch_size = min_blocks_batch
    state = MockState()
    crawler = FunctionCallCrawler(
        state,
        state_provider,
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
    ofp = None
    if outfile is not None:
        ofp = open(outfile, "a")

    try:
        while end_block is None or current_block <= end_block:
            time.sleep(sleep_time)
            until_block = min(
                web3.eth.blockNumber - num_confirmations,
                current_block + current_batch_size,
            )
            if end_block is not None:
                until_block = min(until_block, end_block)
            if until_block < current_block:
                sleep_time *= 2
                continue

            sleep_time /= 2
            if not only_events:
                crawler.crawl(current_block, until_block)
                if state.state:
                    print("Got transaction calls:")
                    for call in state.state:
                        pp.pprint(call, width=200, indent=4)
                        if ofp is not None:
                            print(json.dumps(asdict(call)), file=ofp)
                            ofp.flush()
                    state.flush()

            for event_abi in event_abis:
                all_events, new_batch_size = _crawl_events(
                    event_abi, current_block, until_block, current_batch_size
                )

                if only_events:
                    # Updating batch size only in `--only-events` mode
                    # otherwise it will start taking too much if we also crawl transactions
                    current_batch_size = new_batch_size
                for event in all_events:
                    print("Got event:")
                    pp.pprint(event, width=200, indent=4)
                    if ofp is not None:
                        print(json.dumps(event), file=ofp)
                        ofp.flush()

            progress_bar.set_description(
                f"Current block {until_block}, Already watching for"
            )
            progress_bar.update(until_block - current_block + 1)
            current_block = until_block + 1
    finally:
        if ofp is not None:
            ofp.close()

import pprint as pp
import time
from typing import Any, Dict, List, Optional

import web3
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
) -> None:
    """
    Watches a contract for events and calls.
    """
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
    while True:
        time.sleep(sleep_time)
        end_block = min(web3.eth.blockNumber - num_confirmations, current_block + 100)
        if end_block < current_block:
            sleep_time *= 2
            continue

        sleep_time /= 2

        # crawler.crawl(current_block, end_block)
        if state.state:
            print("Got transaction calls:")
            for call in state.state:
                pp.pprint(call, width=200, indent=4)
            state.flush()

        for event_abi in event_abis:
            all_events = _fetch_events_chunk(
                web3,
                event_abi,
                current_block,
                end_block,
                [contract_address],
            )
            for event in all_events:
                print("Got event:")
                pp.pprint(event, width=200, indent=4)

        progress_bar.set_description(f"Current block {end_block}, Already watching for")
        progress_bar.update(end_block - current_block + 1)
        current_block = end_block + 1

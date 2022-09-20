"""
Implements the moonworm smart contract crawler.

The [`watch_contract`][moonworm.watch.watch_contract] method is the entrypoint to this functionality
and it is what powers the "moonworm watch" command.
"""

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
from .crawler.log_scanner import _crawl_events, _fetch_events_chunk


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
    Watches a contract for events and method calls.

    Currently supports crawling events and direct method calls on a smart contract.

    It does *not* currently support crawling internal messages to a smart contract - this means that any
    calls made to the target smart contract from *another* smart contract will not be recorded directly
    in the crawldata. If the internal message resulted in any events being emitted on the target
    contract, those events *will* be reflected in the crawldata.

    ## Inputs

    1. `web3`: A web3 client used to interact with the blockchain being crawled.
    2. `state_provider`: An [`EthereumStateProvider`][moonworm.crawler.ethereum_state_provider.EthereumStateProvider]
    instance that the crawler uses to access blockchain state and event logs.
    3. `contract_address`: Checksum address for the smart contract
    4. `contract_abi`: List representing objects in the smart contract ABI. It does not need to be an
    exhaustive ABI. Any events not present in the ABI will not be crawled. Any methods not present
    in the ABI will be signalled as warnings by the crawler but not stored in the crawldata.
    5. `num_confirmations`: The crawler will remain this many blocks behind the current head of the blockchain.
    6. `sleep_time`: The number of seconds for which to wait between polls of the state provider. Useful
    if the provider rate limits clients.
    7. `start_block`: Optional block number from which to start the crawl. If not provided, crawl will
    start at block 0.
    8. `end_block`: Optional block number at which to end crawl. If not provided, crawl will continue
    indefinitely.
    9. `min_blocks_batch`: Minimum number of blocks to process at a time. The crawler adapts the batch
    size based on the volume of events and transactions it parses for the contract in its current
    range of blocks.
    10. `min_blocks_batch`: Minimum number of blocks to process at a time. The crawler adapts the batch
    size based on the volume of events and transactions it parses for the contract in its current
    range of blocks.
    11. `max_blocks_batch`: Maximum number of blocks to process at a time. The crawler adapts the batch
    size based on the volume of events and transactions it parses for the contract in its current
    range of blocks.
    12. `batch_size_update_threshold`: Adaptive parameter used to update batch size of blocks crawled
    based on number of events processed in the current batch.
    13. `only_events`: If this argument is set to True, the crawler will only crawl events and ignore
    method calls. Crawling events is much, much faster than crawling method calls.
    14. `outfile`: An optional file to which to write events and/or method calls in [JSON Lines format](https://jsonlines.org/).
    Data is written to this file in append mode, so the crawler never deletes old data.

    ## Outputs

    None. Results are printed to stdout and, if an outfile has been provided, also to the file.
    """

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
                    web3,
                    event_abi,
                    current_block,
                    until_block,
                    current_batch_size,
                    contract_address,
                    batch_size_update_threshold,
                    max_blocks_batch,
                    min_blocks_batch,
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

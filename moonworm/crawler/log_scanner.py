# Used example scanner from web3 documentation : https://web3py.readthedocs.io/en/stable/examples.html#eth-getlogs-limitations
import datetime
import json
import logging
import time
from typing import Any, Callable, Iterable, List, Optional, Tuple

from eth_abi.codec import ABICodec
from eth_typing.evm import ChecksumAddress
from web3 import Web3
from web3._utils.events import get_event_data
from web3._utils.filters import construct_event_filter_params
from web3.datastructures import AttributeDict
from web3.exceptions import BlockNotFound
from web3.types import ABIEvent, FilterParams

from .function_call_crawler import utfy_dict
from .state import EventScannerState

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _retry_web3_call(func, start_block, end_block, retries, delay) -> Tuple[int, list]:
    """A custom retry loop to throttle down block range.

    If our JSON-RPC server cannot serve all incoming `eth_getLogs` in a single request,
    we retry and throttle down block range for every retry.

    For example, Go Ethereum does not indicate what is an acceptable response size.
    It just fails on the server-side with a "context was cancelled" warning.

    :param func: A callable that triggers Ethereum JSON-RPC, as func(start_block, end_block)
    :param start_block: The initial start block of the block range
    :param end_block: The initial start block of the block range
    :param retries: How many times we retry
    :param delay: Time to sleep between retries
    """
    for i in range(retries):
        try:
            return end_block, func(start_block, end_block)
        except Exception as e:
            # Assume this is HTTPConnectionPool(host='localhost', port=8545): Read timed out. (read timeout=10)
            # from Go Ethereum. This translates to the error "context was cancelled" on the server side:
            # https://github.com/ethereum/go-ethereum/issues/20426
            if i < retries - 1:
                # Give some more verbose info than the default middleware
                logger.warning(
                    "Retrying events for block range %d - %d (%d) failed with %s, retrying in %s seconds",
                    start_block,
                    end_block,
                    end_block - start_block,
                    e,
                    delay,
                )
                # Decrease the `eth_getBlocks` range
                end_block = start_block + ((end_block - start_block) // 2)
                # Let the JSON-RPC to recover e.g. from restart
                time.sleep(delay)
                continue
            else:
                logger.warning("Out of retries")
                raise


def _fetch_events_chunk(
    web3,
    event_abi,
    from_block: int,
    to_block: int,
    addresses: Optional[List[ChecksumAddress]] = None,
    on_decode_error: Optional[Callable[[Exception], None]] = None,
) -> List[Any]:
    """Get events using eth_getLogs API.

    Event structure:
    {
        "event": Event name,
        "args": dictionary of event arguments,
        "address": contract address,
        "blockNumber": block number,
        "transactionHash": transaction hash,
        "logIndex": log index
    }

    """

    if from_block is None:
        raise TypeError("Missing mandatory keyword argument to getLogs: fromBlock")

    # Depending on the Solidity version used to compile
    # the contract that uses the ABI,
    # it might have Solidity ABI encoding v1 or v2.
    # We just assume the default that you set on Web3 object here.
    # More information here https://eth-abi.readthedocs.io/en/latest/index.html
    codec: ABICodec = web3.codec

    _, event_filter_params = construct_event_filter_params(
        event_abi,
        codec,
        fromBlock=from_block,
        toBlock=to_block,
    )
    if addresses:
        event_filter_params["address"] = addresses

    logs = web3.eth.get_logs(event_filter_params)

    # Convert raw binary data to Python proxy objects as described by ABI
    all_events = []
    for log in logs:
        try:
            raw_event = get_event_data(codec, event_abi, log)
            event = {
                "event": raw_event["event"],
                "args": json.loads(Web3.toJSON(utfy_dict(dict(raw_event["args"])))),
                "address": raw_event["address"],
                "blockNumber": raw_event["blockNumber"],
                "transactionHash": raw_event["transactionHash"].hex(),
                "logIndex": raw_event["logIndex"],
            }
            all_events.append(event)
        except Exception as e:
            if on_decode_error:
                on_decode_error(e)
            continue
    return all_events


class EventScanner:
    def __init__(
        self,
        web3: Web3,
        events: List,
        addresses: Optional[str] = None,
        scanner_state: Optional[EventScannerState] = None,
        max_chunk_scan_size: int = 10000,
        max_request_retries: int = 30,
        request_retry_seconds: float = 3.0,
        skip_block_timestamp: bool = False,
    ):
        """
        :param events: List of web3 Event we scan
        :param max_chunk_scan_size: JSON-RPC API limit in the number of blocks we query. (Recommendation: 10,000 for mainnet, 500,000 for testnets)
        :param max_request_retries: How many times we try to reattempt a failed JSON-RPC call
        :param request_retry_seconds: Delay between failed requests to let JSON-RPC server to recover
        """

        self.web3 = web3
        self.state = scanner_state
        self.events = events
        self.skip_block_timestamp = skip_block_timestamp

        self.checksum_addresses = []
        if addresses:
            for address in addresses:
                self.checksum_addresses.append(web3.toChecksumAddress(address))

        # Our JSON-RPC throttling parameters
        self.min_scan_chunk_size = 10  # 12 s/block = 120 seconds period
        self.max_scan_chunk_size = max_chunk_scan_size
        self.max_request_retries = max_request_retries
        self.request_retry_seconds = request_retry_seconds

        # Factor how fast we increase the chunk size if results are found
        # # (slow down scan after starting to get hits)
        self.chunk_size_decrease = 0.5

        # Factor how was we increase chunk size if no results found
        self.chunk_size_increase = 2.0

    def get_block_timestamp(self, block_num) -> Optional[datetime.datetime]:
        """Get Ethereum block timestamp"""
        if self.skip_block_timestamp:
            # Returning None since, config set to skip getting block timestamp data
            return None
        try:
            block_info = self.web3.eth.getBlock(block_num)
        except BlockNotFound:
            # Block was not mined yet,
            # minor chain reorganisation?
            return None
        last_time = block_info["timestamp"]
        return datetime.datetime.utcfromtimestamp(last_time)

    def get_suggested_scan_start_block(self):
        """Get where we should start to scan for new token events.

        If there are no prior scans, start from block 1.
        Otherwise, start from the last end block minus ten blocks.
        We rescan the last ten scanned blocks in the case there were forks to avoid
        misaccounting due to minor single block works (happens once in a hour in Ethereum).
        These heurestics could be made more robust, but this is for the sake of simple reference implementation.
        """

        end_block = self.get_last_scanned_block()
        if end_block:
            return max(1, end_block - self.NUM_BLOCKS_RESCAN_FOR_FORKS)
        return 1

    def get_suggested_scan_end_block(self):
        """Get the last mined block on Ethereum chain we are following."""

        # Do not scan all the way to the final block, as this
        # block might not be mined yet
        return self.web3.eth.blockNumber - 1

    def get_last_scanned_block(self) -> int:
        return self.state.get_last_scanned_block()

    def delete_potentially_forked_block_data(self, after_block: int):
        """Purge old data in the case of blockchain reorganisation."""
        self.state.delete_data(after_block)

    def estimate_next_chunk_size(self, current_chuck_size: int, event_found_count: int):
        """Try to figure out optimal chunk size

        Our scanner might need to scan the whole blockchain for all events

        * We want to minimize API calls over empty blocks

        * We want to make sure that one scan chunk does not try to process too many entries once, as we try to control commit buffer size and potentially asynchronous busy loop

        * Do not overload node serving JSON-RPC API by asking data for too many events at a time

        Currently Ethereum JSON-API does not have an API to tell when a first event occured in a blockchain
        and our heuristics try to accelerate block fetching (chunk size) until we see the first event.

        These heurestics exponentially increase the scan chunk size depending on if we are seeing events or not.
        When any transfers are encountered, we are back to scanning only a few blocks at a time.
        It does not make sense to do a full chain scan starting from block 1, doing one JSON-RPC call per 20 blocks.
        """

        if event_found_count > 0:
            # When we encounter first events, reset the chunk size window
            current_chuck_size = self.min_scan_chunk_size
        else:
            current_chuck_size *= self.chunk_size_increase

        current_chuck_size = max(self.min_scan_chunk_size, current_chuck_size)
        current_chuck_size = min(self.max_scan_chunk_size, current_chuck_size)
        return int(current_chuck_size)

    def scan_chunk(self, start_block, end_block) -> Tuple[int, datetime.datetime, list]:
        """Read and process events between to block numbers.

        Dynamically decrease the size of the chunk if the case JSON-RPC server pukes out.

        :return: tuple(actual end block number, when this block was mined, processed events)
        """

        block_timestamps = {}
        get_block_timestamp = self.get_block_timestamp

        # Cache block timestamps to reduce some RPC overhead
        # Real solution might include smarter models around block
        def get_block_when(block_num):
            if block_num not in block_timestamps:
                block_timestamps[block_num] = get_block_timestamp(block_num)
            return block_timestamps[block_num]

        all_processed = []

        for event_type in self.events:

            # Callable that takes care of the underlying web3 call
            def _fetch_events(_start_block, _end_block):
                return _fetch_events_chunk(
                    self.web3,
                    event_type,
                    from_block=_start_block,
                    to_block=_end_block,
                    addresses=self.checksum_addresses,
                )

            # Do `n` retries on `eth_getLogs`,
            # throttle down block range if needed
            end_block, events = _retry_web3_call(
                _fetch_events,
                start_block=start_block,
                end_block=end_block,
                retries=self.max_request_retries,
                delay=self.request_retry_seconds,
            )

            for evt in events:
                idx = evt[
                    "logIndex"
                ]  # Integer of the log index position in the block, null when its pending

                # We cannot avoid minor chain reorganisations, but
                # at least we must avoid blocks that are not mined yet
                assert idx is not None, "Somehow tried to scan a pending block"

                block_number = evt["blockNumber"]

                # Get UTC time when this event happened (block mined timestamp)
                # from our in-memory cache
                block_when = get_block_when(block_number)

                logger.debug(
                    "Processing event %s, block:%d count:%d",
                    evt["event"],
                    evt["blockNumber"],
                )
                processed = self.state.process_event(block_when, evt)
                all_processed.append(processed)

        end_block_timestamp = get_block_when(end_block)
        return end_block, end_block_timestamp, all_processed

    def scan(
        self,
        start_block,
        end_block,
        start_chunk_size=20,
        progress_callback=Optional[Callable],
    ) -> Tuple[list, int]:
        """Perform a token balances scan.

        Assumes all balances in the database are valid before start_block (no forks sneaked in).

        :param start_block: The first block included in the scan

        :param end_block: The last block included in the scan

        :param start_chunk_size: How many blocks we try to fetch over JSON-RPC on the first attempt

        :param progress_callback: If this is an UI application, update the progress of the scan

        :return: [All processed events, number of chunks used]
        """

        assert start_block <= end_block

        current_block = start_block

        # Scan in chunks, commit between
        chunk_size = start_chunk_size
        last_scan_duration = last_logs_found = 0
        total_chunks_scanned = 0

        # All processed entries we got on this scan cycle
        all_processed = []

        while current_block <= end_block:

            self.state.start_chunk(current_block, chunk_size)

            # Print some diagnostics to logs to try to fiddle with real world JSON-RPC API performance
            estimated_end_block = current_block + chunk_size
            logger.debug(
                "Scanning token transfers for blocks: %d - %d, chunk size %d, last chunk scan took %f, last logs found %d",
                current_block,
                estimated_end_block,
                chunk_size,
                last_scan_duration,
                last_logs_found,
            )

            start = time.time()
            actual_end_block, end_block_timestamp, new_entries = self.scan_chunk(
                current_block, estimated_end_block
            )

            # Where does our current chunk scan ends - are we out of chain yet?
            current_end = actual_end_block

            last_scan_duration = time.time() - start
            all_processed += new_entries

            # Print progress bar
            if progress_callback:
                progress_callback(
                    start_block,
                    end_block,
                    current_block,
                    end_block_timestamp,
                    chunk_size,
                    len(new_entries),
                )

            # Try to guess how many blocks to fetch over `eth_getLogs` API next time
            chunk_size = self.estimate_next_chunk_size(chunk_size, len(new_entries))

            # Set where the next chunk starts
            current_block = current_end + 1
            total_chunks_scanned += 1
            self.state.end_chunk(current_end)

        return all_processed, total_chunks_scanned

import os
import pickle
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from typing import Any, Dict, List

from eth_typing.evm import ChecksumAddress
from web3 import Web3
from web3.contract import Contract
from web3.types import ABI

from moonworm.contracts import ERC1155


@dataclass
class ContractFunctionCall:
    block_number: int
    block_timestamp: int
    transaction_hash: str
    contract_address: str
    caller_address: str
    function_name: str
    function_args: Dict[str, Any]


class EthereumStateProvider(ABC):
    """
    Abstract class for Ethereum state provider.
    If you want to use a different state provider, you can implement this class.
    """

    @abstractmethod
    def get_last_block_number(self) -> int:
        """
        Returns the last block number.
        """
        pass

    @abstractmethod
    def get_block_timestamp(self, block_number: int) -> int:
        """
        Returns the timestamp of the block with the given block number.
        """
        pass

    @abstractmethod
    def get_transactions_to_address(
        self, address, block_number: int
    ) -> List[Dict[str, Any]]:
        """
        Returns all transactions to the given address in the given block number.
        """
        pass


class FunctionCallCrawlerState(ABC):
    """
    Abstract class for function call crawler state.
    If you want to use a different state, you can implement this class.
    """

    @abstractmethod
    def get_last_crawled_block(self) -> int:
        """
        Returns the last block number that was crawled.
        """
        pass

    @abstractmethod
    def register_call(self, function_call: ContractFunctionCall) -> None:
        """
        Processes the given function call (store it, etc.).
        """
        pass

    @abstractmethod
    def flush(self) -> None:
        """
        Flushes cached state to storage layer.
        """
        pass


class PickleFileState(FunctionCallCrawlerState):
    """
    Implements the FunctionCallCrawlerState interface using a JSON file in which to store the safe.

    Note: Does not implement any file lock on the JSON file, and assumes that no other process is
    modifying the file at the same time. Does not perform atomic write to the file, either, so
    readers beware.
    """

    def __init__(self, pickle_file: str, batch_size: int = 100):
        initial_state = {
            "last_crawled_block": -1,
            "calls": [],
        }

        self.state = initial_state

        if not os.path.exists(pickle_file):
            with open(pickle_file, "wb") as ofp:
                pickle.dump(initial_state, ofp)
        else:
            with open(pickle_file, "rb") as ifp:
                self.state = pickle.load(ifp)
        self.pickle_file = pickle_file

        self.state_file = pickle_file
        self.batch_size = batch_size
        self.cache_size = 0

    def get_last_crawled_block(self) -> int:
        return self.state.get("last_crawled_block")

    def register_call(self, function_call: ContractFunctionCall) -> None:
        self.state["calls"].append(asdict(function_call))
        self.cache_size += 1
        self.state["last_crawled_block"] = function_call.block_number
        if self.cache_size == self.batch_size:
            self.flush()

    def flush(self) -> None:
        with open(self.pickle_file, "wb") as ofp:
            pickle.dump(self.state, ofp)
        self.cache_size = 0


class Web3StateProvider(EthereumStateProvider):
    """
    Implementation of EthereumStateProvider with web3.
    """

    def __init__(self, w3: Web3):
        self.w3 = w3
        self.blocks_cache = {}

    def get_last_block_number(self) -> int:
        return self.w3.eth.block_number

    def _get_block(self, block_number: int) -> Dict[str, Any]:
        if block_number in self.blocks_cache:
            return self.blocks_cache[block_number]
        block = self.w3.eth.getBlock(block_number, full_transactions=True)

        # clear cache if it grows too large
        if len(self.blocks_cache) > 50:
            self.blocks_cache = {}

        self.blocks_cache[block_number] = block
        return block

    def get_block_timestamp(self, block_number: int) -> int:
        block = self._get_block(block_number)
        return block["timestamp"]

    def get_transactions_to_address(
        self, address: ChecksumAddress, block_number: int
    ) -> List[Dict[str, Any]]:
        block = self._get_block(block_number)

        all_transactions = block["transactions"]
        return [tx for tx in all_transactions if tx["to"] == address]


class FunctionCallCrawler:
    """
    Crawls the Ethereum blockchain for function calls.
    """

    def __init__(
        self,
        state: FunctionCallCrawlerState,
        ethereum_state_provider: EthereumStateProvider,
        contract_abi: List[Dict[str, Any]],
        contract_addresses: List[ChecksumAddress],
    ):
        self.state = state
        self.ethereum_state_provider = ethereum_state_provider
        self.contract_abi = contract_abi
        self.contract_addresses = contract_addresses
        self.contract = Web3().eth.contract(abi=self.contract_abi)

    def process_transaction(self, transaction: Dict[str, Any]):
        try:
            raw_function_call = self.contract.decode_function_input(
                transaction["input"]
            )
            function_name = raw_function_call[0].fn_name
            function_args = raw_function_call[1]
            function_call = ContractFunctionCall(
                block_number=transaction["blockNumber"],
                block_timestamp=self.ethereum_state_provider.get_block_timestamp(
                    transaction["blockNumber"]
                ),
                transaction_hash=transaction["hash"],
                contract_address=transaction["to"],
                caller_address=transaction["from"],
                function_name=function_name,
                function_args=function_args,
            )
            self.state.register_call(function_call)
        except Exception as e:
            print(f"Failed to decode function call in tx: {transaction['hash'].hex()}")

    def crawl(self, from_block: int, to_block: int, flush_state: bool = False):
        for block_number in range(from_block, to_block + 1):
            for address in self.contract_addresses:
                transactions = self.ethereum_state_provider.get_transactions_to_address(
                    address, block_number
                )
                for transaction in transactions:
                    self.process_transaction(transaction)
            self.state.state
        if flush_state:
            self.state.flush()

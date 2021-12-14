import os
import pickle
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from logging import error
from typing import Any, Callable, Dict, List, Optional

from eth_typing.evm import ChecksumAddress
from web3 import Web3
from web3.contract import Contract
from web3.types import ABI

from moonworm.contracts import ERC1155

from .ethereum_state_provider import EthereumStateProvider, Web3StateProvider


@dataclass
class ContractFunctionCall:
    block_number: int
    block_timestamp: int
    transaction_hash: str
    contract_address: str
    caller_address: str
    function_name: str
    function_args: Dict[str, Any]
    gas_used: int
    status: int


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


# b'\x8d\xa5\xcb['
# Need to utfy because args contains bytes
# For now casting to hex, because that byte at top is function signature
# .decode() fails
def utfy_dict(dic):
    if isinstance(dic, str):
        return dic

    elif isinstance(dic, bytes):
        return Web3().toHex(dic)

    elif isinstance(dic, tuple):
        return tuple(utfy_dict(x) for x in dic)
    elif isinstance(dic, dict):
        for key in dic:
            dic[key] = utfy_dict(dic[key])
        return dic
    elif isinstance(dic, list):
        new_l = []
        for e in dic:
            new_l.append(utfy_dict(e))
        return new_l
    else:
        return dic


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
        on_decode_error: Optional[Callable[[Exception], None]] = None,
    ):
        self.state = state
        self.ethereum_state_provider = ethereum_state_provider
        self.contract_abi = contract_abi
        self.contract_addresses = contract_addresses
        self.contract = Web3().eth.contract(abi=self.contract_abi)
        self.on_decode_error = on_decode_error

    def process_transaction(self, transaction: Dict[str, Any]):
        try:
            raw_function_call = self.contract.decode_function_input(
                transaction["input"]
            )
            function_name = raw_function_call[0].fn_name

            function_args = utfy_dict(raw_function_call[1])

            # TODO: check transaction reciept for none
            transaction_reciept = self.ethereum_state_provider.get_transaction_reciept(
                transaction["hash"]
            )

            function_call = ContractFunctionCall(
                block_number=transaction["blockNumber"],
                block_timestamp=self.ethereum_state_provider.get_block_timestamp(
                    transaction["blockNumber"]
                ),
                transaction_hash=transaction["hash"].hex(),
                contract_address=transaction["to"],
                caller_address=transaction["from"],
                function_name=function_name,
                function_args=function_args,
                status=transaction_reciept["status"],
                gas_used=transaction_reciept["gasUsed"],
            )

            self.state.register_call(function_call)
        except Exception as e:
            print(f"Failed to decode function call in tx: {transaction['hash'].hex()}")
            if self.on_decode_error:
                self.on_decode_error(e)
            print(e)

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

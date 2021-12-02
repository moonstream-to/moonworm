import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union

from eth_typing.evm import ChecksumAddress
from web3 import Web3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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


class Web3StateProvider(EthereumStateProvider):
    """
    Implementation of EthereumStateProvider with web3.
    """

    def __init__(self, w3: Web3):
        self.w3 = w3

        self.blocks_cache = {}

    def get_transaction_reciept(self, transaction_hash: str) -> Dict[str, Any]:
        return self.w3.eth.get_transaction_receipt(transaction_hash)

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

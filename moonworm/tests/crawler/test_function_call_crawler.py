import os
import pickle
import shutil
import tempfile
import unittest
from typing import Any, Dict, List

import web3
from web3.main import Web3

from moonworm.contracts import ERC20
from moonworm.crawler.function_call_crawler import (
    EthereumStateProvider,
    FunctionCallCrawler,
    PickleFileState,
    Web3StateProvider,
)


class EthereumTesterStateProvider(EthereumStateProvider):
    """
    This wrapper is necessary because the EthereumTesterProvider returns different attributes on
    transaction objects than we would receive from a proper Ethereum JSON RPC API.
    """

    def __init__(self, web3_state_provider: Web3StateProvider):
        self.internal_provider = web3_state_provider

    def get_last_block_number(self) -> int:
        return self.internal_provider.get_last_block_number()

    def get_block_timestamp(self, block_number: int) -> int:
        return self.internal_provider.get_block_timestamp(block_number)

    def get_transactions_to_address(
        self, address: str, block_number: int
    ) -> List[Dict[str, Any]]:
        transactions = self.internal_provider.get_transactions_to_address(
            address, block_number
        )

        return [
            {
                "input": transaction["data"],
                "blockNumber": transaction["block_number"],
                **transaction,
            }
            for transaction in transactions
        ]


class TestFunctionCallCrawlerWithERC20Token(unittest.TestCase):
    """
    Tests the FunctionCallCrawler using:
    1. web3.EthereumTesterProvider to provide blockchain state.
    2. moonworm.crawler.function_call_crawler.PickleFileState to provide crawler state from a temporary file.
    3. A fresh ERC20 token deployment with some test function calls to test against.
    """

    def setUp(self) -> None:
        self.web3_client = web3.Web3(web3.EthereumTesterProvider())
        self.crawldir = tempfile.mkdtemp()
        self.pickle_file = os.path.join(self.crawldir, "state.pkl")

        self.internal_web3_state = Web3StateProvider(self.web3_client)
        self.web3_state = EthereumTesterStateProvider(self.internal_web3_state)
        self.crawler_state = PickleFileState(self.pickle_file)

        self.web3_client.eth.default_account = self.web3_client.eth.accounts[0]

        self.token_name = "Test ERC20 token"
        self.token_symbol = "TEST"
        self.deployment_transaction = (
            self.web3_client.eth.contract(abi=ERC20.abi(), bytecode=ERC20.bytecode())
            .constructor(
                self.token_name, self.token_symbol, self.web3_client.eth.accounts[0]
            )
            .transact()
        )
        deployment_transaction_receipt = (
            self.web3_client.eth.wait_for_transaction_receipt(
                self.deployment_transaction
            )
        )
        self.contract_address = deployment_transaction_receipt.contractAddress

        self.start_block = self.web3_client.eth.block_number

        self.contract = self.web3_client.eth.contract(
            address=self.contract_address, abi=ERC20.abi()
        )

        self.mint_amount = 1000
        self.mint_transaction = self.contract.functions.mint(
            self.web3_client.eth.accounts[0], self.mint_amount
        ).transact({"from": self.web3_client.eth.accounts[0]})
        self.mint_transaction_receipt = (
            self.web3_client.eth.wait_for_transaction_receipt(self.mint_transaction)
        )

        self.end_block = self.web3_client.eth.block_number

    def tearDown(self) -> None:
        shutil.rmtree(self.crawldir)

    def test_call_crawler(self) -> None:
        crawler = FunctionCallCrawler(
            self.crawler_state, self.web3_state, ERC20.abi(), [self.contract_address]
        )
        crawler.crawl(self.start_block, self.end_block)

        mint_block_number = self.mint_transaction_receipt["blockNumber"]
        mint_block = self.web3_client.eth.get_block(mint_block_number)

        expected_calls = [
            {
                "block_number": mint_block_number,
                "block_timestamp": mint_block["timestamp"],
                "caller_address": self.web3_client.eth.accounts[0],
                "contract_address": self.contract_address,
                "function_name": "mint",
                "function_args": {
                    "account": self.web3_client.eth.accounts[0],
                    "amount": self.mint_amount,
                },
                "transaction_hash": self.mint_transaction_receipt["transactionHash"],
            },
        ]

        self.assertListEqual(crawler.state.state["calls"], expected_calls)

        crawler.state.flush()

        expected_crawler_state = {
            "last_crawled_block": self.end_block,
            "calls": expected_calls,
        }
        with open(self.pickle_file, "rb") as ifp:
            crawler_state = pickle.load(ifp)
        self.assertDictEqual(crawler_state, expected_crawler_state)


if __name__ == "__main__":
    unittest.main()

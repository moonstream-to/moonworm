import os
from typing import Tuple
import unittest

from eth_typing.evm import ChecksumAddress
from web3 import Web3, EthereumTesterProvider, eth
import web3

from .web3_util import get_nonce, submit_signed_raw_transaction, submit_transaction

PK = "0x58d23b55bc9cdce1f18c2500f40ff4ab7245df9a89505e9b1fa4851f623d241d"
PK_ADDRESS = "0xdc544d1aa88ff8bbd2f2aec754b1f1e99e1812fd"


def read_testnet_env_variables() -> Tuple[ChecksumAddress, str]:
    raw_address = os.environ.get("CENTIPEDE_ETHEREUM_ADDRESS")
    if raw_address is None:
        raise ValueError("CENTIPEDE_ETHEREUM_ADDRESS is not set")
    private_key = os.environ.get("CENTIPEDE_ETHEREUM_ADDRESS_PRIVATE_KEY")
    if raw_address is None:
        raise ValueError("CENTIPEDE_ETHEREUM_ADDRESS_PRIVATE_KEY is not set")
    return (Web3.toChecksumAddress(raw_address), private_key)


def get_web3_test_provider() -> Web3:
    return Web3(EthereumTesterProvider())


class CentipedeTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.web3 = get_web3_test_provider()
        tx_hash = self.web3.eth.send_transaction(
            {
                "from": self.web3.eth.accounts[0],
                "to": Web3.toChecksumAddress(PK_ADDRESS),
                "value": 1000000,
            }
        )
        self.web3.eth.wait_for_transaction_receipt(tx_hash)

    def test_submit_transaction(self) -> None:

        sender = Web3.toChecksumAddress(PK_ADDRESS)
        self.web3.eth.send_transaction
        receiver = Web3.toChecksumAddress(self.web3.eth.accounts[1])

        current_sender_balance = self.web3.eth.get_balance(sender)
        print(current_sender_balance)
        current_receiver_balance = self.web3.eth.get_balance(receiver)
        print(current_receiver_balance)
        transaction = {
            "from": sender,
            "to": receiver,
            "value": 10,
            "nonce": get_nonce(self.web3, sender),
            "gasPrice": 1,
        }
        transaction["gas"] = self.web3.eth.estimate_gas(transaction)

        receipt = submit_transaction(
            self.web3,
            transaction,
            PK,
        )
        print(receipt)

        current_sender_balance = self.web3.eth.get_balance(sender)
        print(current_sender_balance)
        current_receiver_balance = self.web3.eth.get_balance(receiver)
        print(current_receiver_balance)

    def test_submit_signed_transaction(self) -> None:

        sender = Web3.toChecksumAddress(PK_ADDRESS)
        self.web3.eth.send_transaction
        receiver = Web3.toChecksumAddress(self.web3.eth.accounts[1])

        current_sender_balance = self.web3.eth.get_balance(sender)
        print(current_sender_balance)
        current_receiver_balance = self.web3.eth.get_balance(receiver)
        print(current_receiver_balance)
        transaction = {
            "from": sender,
            "to": receiver,
            "value": 10,
            "nonce": get_nonce(self.web3, sender),
            "gasPrice": 1,
        }
        transaction["gas"] = self.web3.eth.estimate_gas(transaction)

        signed_transaction = self.web3.eth.account.sign_transaction(
            transaction, private_key=PK
        )

        receipt = submit_signed_raw_transaction(
            self.web3, signed_transaction.rawTransaction
        )
        print(receipt)

        current_sender_balance = self.web3.eth.get_balance(sender)
        print(current_sender_balance)
        current_receiver_balance = self.web3.eth.get_balance(receiver)
        print(current_receiver_balance)

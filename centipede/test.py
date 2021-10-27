import os
from typing import Tuple
import unittest

from eth_typing.evm import ChecksumAddress
from web3 import Web3, EthereumTesterProvider
from ens import ENS

from centipede.manage import deploy_ERC1155
from .web3_util import (
    build_transaction,
    decode_transaction_input,
    get_nonce,
    submit_signed_raw_transaction,
    submit_transaction,
    wait_for_transaction_receipt,
)

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


def airdrop_ether(web3: Web3, to_address: ChecksumAddress):
    tx_hash = web3.eth.send_transaction(
        {
            "from": web3.eth.accounts[0],
            "to": to_address,
            "value": 100000000,
        }
    )
    web3.eth.wait_for_transaction_receipt(tx_hash)


class CentipedeEthTesterTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.web3 = get_web3_test_provider()
        self.tester_address = Web3.toChecksumAddress(PK_ADDRESS)
        self.tester_address_pk = PK
        airdrop_ether(self.web3, self.tester_address)

    def check_eth_send(
        self,
        sender_previous_balance,
        receiver_previous_balance,
        sender_current_balance,
        receiver_current_balance,
        send_value,
        tx_receipt,
    ):

        assert receiver_current_balance == receiver_previous_balance + send_value
        assert (
            sender_current_balance
            == sender_previous_balance - send_value - tx_receipt["gasUsed"]
        )

    def test_submit_transaction(self) -> None:

        sender = Web3.toChecksumAddress(PK_ADDRESS)
        self.web3.eth.send_transaction
        receiver = Web3.toChecksumAddress(self.web3.eth.accounts[1])

        sender_previous_balance = self.web3.eth.get_balance(sender)
        receiver_previous_balance = self.web3.eth.get_balance(receiver)
        send_value = 10
        transaction = {
            "from": sender,
            "to": receiver,
            "value": send_value,
            "nonce": get_nonce(self.web3, sender),
            "gasPrice": 1,
        }
        transaction["gas"] = self.web3.eth.estimate_gas(transaction)

        tx_hash = submit_transaction(
            self.web3,
            transaction,
            PK,
        )
        tx_receipt = wait_for_transaction_receipt(self.web3, tx_hash)
        sender_current_balance = self.web3.eth.get_balance(sender)
        receiver_current_balance = self.web3.eth.get_balance(receiver)
        self.check_eth_send(
            sender_previous_balance,
            receiver_previous_balance,
            sender_current_balance,
            receiver_current_balance,
            send_value,
            tx_receipt,
        )

    def test_submit_signed_transaction(self) -> None:

        sender = Web3.toChecksumAddress(PK_ADDRESS)
        self.web3.eth.send_transaction
        receiver = Web3.toChecksumAddress(self.web3.eth.accounts[1])

        sender_previous_balance = self.web3.eth.get_balance(sender)
        receiver_previous_balance = self.web3.eth.get_balance(receiver)
        send_value = 10

        transaction = {
            "from": sender,
            "to": receiver,
            "value": send_value,
            "nonce": get_nonce(self.web3, sender),
            "gasPrice": 1,
        }
        transaction["gas"] = self.web3.eth.estimate_gas(transaction)

        signed_transaction = self.web3.eth.account.sign_transaction(
            transaction, private_key=PK
        )

        tx_hash = submit_signed_raw_transaction(
            self.web3, signed_transaction.rawTransaction
        )
        tx_receipt = wait_for_transaction_receipt(self.web3, tx_hash)
        sender_current_balance = self.web3.eth.get_balance(sender)
        receiver_current_balance = self.web3.eth.get_balance(receiver)
        self.check_eth_send(
            sender_previous_balance,
            receiver_previous_balance,
            sender_current_balance,
            receiver_current_balance,
            send_value,
            tx_receipt,
        )

    def test_deploy_erc1155(self):
        TOKEN_NAME = "CENTIPEDE-TEST"
        TOKEN_SYMBOL = "CNTPD"
        TOKEN_URI = "moonstream.to/centipede/"
        contract_address = deploy_ERC1155(
            self.web3,
            TOKEN_NAME,
            TOKEN_SYMBOL,
            TOKEN_URI,
            self.tester_address,
            self.tester_address,
            self.tester_address_pk,
        )

        base_dir = os.path.dirname(__file__)
        contract_abi_path = os.path.join(base_dir, "fixture/abis/ERC1155.json")
        with open(contract_abi_path, "r") as ifp:
            contract_abi = ifp.read()

        contract = self.web3.eth.contract(contract_address, abi=contract_abi)

        assert (
            contract.functions["name"]().call() == TOKEN_NAME
        ), "Token name in blockchain != set token name while deploying"

        assert (
            contract.functions["symbol"]().call() == TOKEN_SYMBOL
        ), "Token name in blockchain != set token symbol while deploying"

        transaction = build_transaction(
            self.web3, contract.functions["create"]("1", b""), self.tester_address
        )
        tx_hash = submit_transaction(self.web3, transaction, self.tester_address_pk)
        wait_for_transaction_receipt(self.web3, tx_hash)

        assert (
            contract.functions["uri"](1).call() == TOKEN_URI + "1"
        ), "Token with id 1 is not created or has different uri from that is expected"

    def test_decode_tx_input(self):
        base_dir = os.path.dirname(__file__)
        contract_abi_path = os.path.join(base_dir, "fixture/abis/ERC1155.json")
        with open(contract_abi_path, "r") as ifp:
            contract_abi = ifp.read()
        tx_input = "0xf242432a0000000000000000000000004f9a8e7dddee5f9737bafad382fa3bb119fc80c4000000000000000000000000c2485a4a8fbabbb7c39fe7b459816f2f16c238840000000000000000000000000000000000000000000000000000000000000378000000000000000000000000000000000000000000000000000000000000000100000000000000000000000000000000000000000000000000000000000000a00000000000000000000000000000000000000000000000000000000000000000"
        print(decode_transaction_input(self.web3, tx_input, contract_abi))

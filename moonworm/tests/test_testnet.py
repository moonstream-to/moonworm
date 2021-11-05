import os
import unittest
from typing import Tuple
from unittest.case import TestCase

from eth_typing.evm import ChecksumAddress
from web3 import Web3

from moonworm.contracts import ERC1155
from moonworm.web3_util import build_transaction, submit_transaction

from ..manage import deploy_ERC1155


def read_testnet_env_variables() -> Tuple[Web3, ChecksumAddress, str]:
    provider_path = os.environ.get("MOONWORM_TESTNET_PATH")
    if provider_path is None:
        raise ValueError("MOONWORM_TESTNET_PATH env variable is not set")
    raw_address = os.environ.get("MOONWORM_TEST_ETHEREUM_ADDRESS")
    if raw_address is None:
        raise ValueError("MOONWORM_TEST_ETHEREUM_ADDRESS env variable is not set")
    private_key = os.environ.get("MOONWORM_TEST_ETHEREUM_ADDRESS_PRIVATE_KEY")
    if raw_address is None:
        raise ValueError(
            "MOONWORM_TEST_ETHEREUM_ADDRESS_PRIVATE_KEY env variable is not set"
        )
    return (
        Web3(Web3.HTTPProvider(provider_path)),
        Web3.toChecksumAddress(raw_address),
        private_key,
    )


class MoonwormTestnetTestCase(TestCase):
    def setUp(self) -> None:
        self.basedir = os.path.dirname(os.path.dirname(__file__))
        try:
            (
                self.web3,
                self.test_address,
                self.test_address_pk,
            ) = read_testnet_env_variables()
        except Exception as e:
            raise unittest.SkipTest(f"Skipping test because of : {str(e)}")

    def _deploy_contract(self) -> ChecksumAddress:
        TOKEN_NAME = "MOONWORM=TEST"
        TOKEN_SYMBOL = "CNTPD"
        TOKEN_URI = "moonstream.to/moonworm/"
        _, contract_address = deploy_ERC1155(
            self.web3,
            TOKEN_NAME,
            TOKEN_SYMBOL,
            TOKEN_URI,
            self.test_address,
            self.test_address,
            self.test_address_pk,
        )
        return contract_address

    def test_deployment(self) -> None:
        contract_address = self._deploy_contract()
        contract = self.web3.eth.contract(contract_address, abi=ERC1155.abi())

        tx = build_transaction(
            self.web3, contract.functions["create"]("1", b""), self.test_address
        )

        submit_transaction(self.web3, tx, self.test_address_pk)


if __name__ == "__main__":
    unittest.main()

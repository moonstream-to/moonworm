from typing import Any, Dict, List, Optional, Tuple
import os


from eth_typing.evm import ChecksumAddress
from hexbytes.main import HexBytes
from web3 import Web3
from web3.contract import ContractFunction
from web3.types import Nonce, TxParams, TxReceipt, Wei


def build_transaction(
    web3: Web3,
    builder: ContractFunction,
    sender: ChecksumAddress,
    maxFeePerGas: Optional[Wei] = None,
    maxPriorityFeePerGas: Optional[Wei] = None,
):
    transaction = builder.buildTransaction(
        {
            "from": sender,
            "maxFeePerGas": maxFeePerGas,
            "maxPriorityFeePerGas": maxPriorityFeePerGas,
            "nonce": get_nonce(web3, sender),
        }
    )
    return transaction


def get_nonce(web3: Web3, sender: ChecksumAddress) -> Nonce:
    nonce = web3.eth.get_transaction_count(sender)
    return nonce


def submit_transaction(
    web3: Web3, transaction: Dict[str, Any], signer_private_key: str
) -> TxReceipt:
    signed_transaction = web3.eth.account.sign_transaction(
        transaction, private_key=signer_private_key
    )
    return submit_signed_raw_transaction(web3, signed_transaction.rawTransaction)


def submit_signed_raw_transaction(
    web3: Web3, signed_raw_transaction: HexBytes
) -> TxReceipt:

    transaction_hash = web3.eth.send_raw_transaction(signed_raw_transaction)
    transaction_receipt = web3.eth.wait_for_transaction_receipt(transaction_hash)
    return transaction_receipt


def deploy_contract(
    web3: Web3,
    contract_bytecode: str,
    contract_abi: Dict[str, Any],
    deployer: ChecksumAddress,
    deployer_private_key: str,
    constructor_arguments: Optional[List[Any]] = None,
):
    contract = web3.eth.contract(abi=contract_abi, bytecode=contract_bytecode)
    transaction = build_transaction(
        web3, contract.constructor(*constructor_arguments), deployer
    )
    transaction_receipt = submit_transaction(web3, transaction, deployer_private_key)
    contract_address = transaction_receipt.contractAddress
    return contract_address


def read_keys_from_cli() -> Tuple[ChecksumAddress, str]:
    raw_address = input("Enter your ethereum address:")
    private_key = input("Enter private key of your address:")
    return (Web3.toChecksumAddress(raw_address), private_key)


def read_keys_from_env() -> Tuple[ChecksumAddress, str]:
    raw_address = os.environ.get("CENTIPEDE_ETHEREUM_ADDRESS")
    if raw_address is None:
        raise ValueError("CENTIPEDE_ETHEREUM_ADDRESS is not set")
    private_key = os.environ.get("CENTIPEDE_ETHEREUM_ADDRESS_PRIVATE_KEY")
    if raw_address is None:
        raise ValueError("CENTIPEDE_ETHEREUM_ADDRESS_PRIVATE_KEY is not set")
    return (Web3.toChecksumAddress(raw_address), private_key)

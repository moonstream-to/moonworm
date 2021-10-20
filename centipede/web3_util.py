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
            # "maxFeePerGas": maxFeePerGas,
            # "maxPriorityFeePerGas": maxPriorityFeePerGas,
            "nonce": get_nonce(web3, sender),
        }
    )
    return transaction


def get_nonce(web3: Web3, sender: ChecksumAddress) -> Nonce:
    nonce = web3.eth.get_transaction_count(sender)
    return nonce


def submit_transaction(
    web3: Web3, transaction: Dict[str, Any], signer_private_key: str
) -> HexBytes:
    signed_transaction = web3.eth.account.sign_transaction(
        transaction, private_key=signer_private_key
    )
    return submit_signed_raw_transaction(web3, signed_transaction.rawTransaction)


def submit_signed_raw_transaction(
    web3: Web3, signed_raw_transaction: HexBytes
) -> HexBytes:

    transaction_hash = web3.eth.send_raw_transaction(signed_raw_transaction)
    return transaction_hash


def wait_for_transaction_receipt(web3: Web3, transaction_hash: HexBytes):
    return web3.eth.wait_for_transaction_receipt(transaction_hash)


def deploy_contract(
    web3: Web3,
    contract_bytecode: str,
    contract_abi: Dict[str, Any],
    deployer: ChecksumAddress,
    deployer_private_key: str,
    constructor_arguments: Optional[List[Any]] = None,
) -> str:
    contract = web3.eth.contract(abi=contract_abi, bytecode=contract_bytecode)
    transaction = build_transaction(
        web3, contract.constructor(*constructor_arguments), deployer
    )

    transaction_hash = submit_transaction(web3, transaction, deployer_private_key)
    transaction_receipt = wait_for_transaction_receipt(web3, transaction_hash)
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


def deploy_ERC1155(
    web3: Web3,
    token_name: str,
    token_symbol: str,
    token_uri: str,
    token_owner: ChecksumAddress,
    deployer: ChecksumAddress,
    deployer_private_key: str,
) -> str:
    base_dir = os.path.dirname(__file__)
    contract_bytecode_path = os.path.join(base_dir, "fixture/bytecodes/ERC1155.bin")
    with open(contract_bytecode_path, "r") as ifp:
        contract_bytecode = ifp.read()

    contract_abi_path = os.path.join(base_dir, "fixture/abis/ERC1155.json")
    with open(contract_abi_path, "r") as ifp:
        contract_abi = ifp.read()

    contract_address = deploy_contract(
        web3,
        contract_bytecode,
        contract_abi,
        deployer,
        deployer_private_key,
        [token_name, token_symbol, token_uri, token_owner],
    )

    return contract_address

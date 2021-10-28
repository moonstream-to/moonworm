import os
from typing import Any, Dict, List, Optional, Tuple, Type, Union

from eth_typing.evm import ChecksumAddress
import web3
from web3 import Web3
from web3.contract import Contract
from web3.types import ABIEvent, ABIFunction

from .web3_util import deploy_contract


def init_web3(ipc_path: str) -> Web3:
    return Web3(web3.HTTPProvider(ipc_path))


def init_contract(
    web3: Web3, abi: Dict[str, Any], address: Optional[str]
) -> Union[Contract, Type[Contract]]:
    checksum_address: Optional[ChecksumAddress] = None
    if address is not None:
        checksum_address = web3.toChecksumAddress(address)
    return web3.eth.contract(address=checksum_address, abi=abi)


def abi_show(abi: Dict[str, Any]) -> Tuple[List[ABIFunction], List[ABIEvent]]:
    abi_functions = [item for item in abi if item["type"] == "function"]
    abi_events = [item for item in abi if item["type"] == "event"]
    return (abi_functions, abi_events)


def call_function(contract: Contract, function_name, *args) -> Any:
    contract.functions[function_name]().call(*args)


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
    contract_bytecode_path = os.path.join(
        base_dir, "fixture/bytecodes/CentipedeERC1155.bin"
    )
    with open(contract_bytecode_path, "r") as ifp:
        contract_bytecode = ifp.read()

    contract_abi_path = os.path.join(base_dir, "fixture/abis/CentipedeERC1155.json")
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

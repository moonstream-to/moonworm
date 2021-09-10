from dataclasses import dataclass
from os import name
from typing import Any, Dict, List, Optional, Tuple

from eth_typing.evm import ChecksumAddress
import web3
from web3 import Web3
from web3.contract import Contract
from web3.types import ABIEvent, ABIFunction


def init_web3(ipc_path: str) -> Web3:
    return web3.HTTPProvider(ipc_path)


def init_contract(web3: Web3, abi: Dict[str, Any], address: Optional[str]) -> Contract:
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

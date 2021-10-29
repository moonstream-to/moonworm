import os
from typing import Any, Dict, List, Optional, Tuple, Type, Union

from eth_typing.evm import ChecksumAddress
from hexbytes.main import HexBytes
import web3
from web3 import Web3
from web3.contract import Contract
from web3.types import ABIEvent, ABIFunction

from centipede.contracts import ERC1155, CentipedeContract

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


def _deploy_centipede_token_contract(
    web3: Web3,
    contract_class: CentipedeContract,
    token_name: str,
    token_symbol: str,
    token_uri: str,
    token_owner: ChecksumAddress,
    deployer: ChecksumAddress,
    deployer_private_key: str,
):
    contract_abi = contract_class.abi()
    contract_bytecode = contract_class.bytecode()
    return deploy_contract(
        web3,
        contract_bytecode,
        contract_abi,
        deployer,
        deployer_private_key,
        [token_name, token_symbol, token_uri, token_owner],
    )


def deploy_ERC1155(
    web3: Web3,
    token_name: str,
    token_symbol: str,
    token_uri: str,
    token_owner: ChecksumAddress,
    deployer: ChecksumAddress,
    deployer_private_key: str,
) -> Tuple[HexBytes, ChecksumAddress]:
    return _deploy_centipede_token_contract(
        web3,
        ERC1155,
        token_name,
        token_symbol,
        token_uri,
        token_owner,
        deployer,
        deployer_private_key,
    )

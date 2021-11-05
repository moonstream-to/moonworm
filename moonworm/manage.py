from typing import Tuple

from eth_typing.evm import ChecksumAddress
from hexbytes.main import HexBytes
from web3 import Web3

from .contracts import ERC20, ERC721, ERC1155, MoonwormContract
from .web3_util import deploy_contract


def _deploy_moonworm_token_contract(
    web3: Web3,
    contract_class: MoonwormContract,
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
    return _deploy_moonworm_token_contract(
        web3,
        ERC1155,
        token_name,
        token_symbol,
        token_uri,
        token_owner,
        deployer,
        deployer_private_key,
    )


def deploy_ERC20(
    web3: Web3,
    token_name: str,
    token_symbol: str,
    token_owner: ChecksumAddress,
    deployer: ChecksumAddress,
    deployer_private_key: str,
) -> Tuple[HexBytes, ChecksumAddress]:
    contract_abi = ERC20.abi()
    contract_bytecode = ERC20.bytecode()
    return deploy_contract(
        web3,
        contract_bytecode,
        contract_abi,
        deployer,
        deployer_private_key,
        [token_name, token_symbol, token_owner],
    )


def deploy_ERC721(
    web3: Web3,
    token_name: str,
    token_symbol: str,
    token_uri: str,
    token_owner: ChecksumAddress,
    deployer: ChecksumAddress,
    deployer_private_key: str,
) -> Tuple[HexBytes, ChecksumAddress]:
    return _deploy_moonworm_token_contract(
        web3,
        ERC721,
        token_name,
        token_symbol,
        token_uri,
        token_owner,
        deployer,
        deployer_private_key,
    )

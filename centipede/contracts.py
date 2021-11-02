import json
import os
from typing import Any, Dict


_PATHS = {
    "abi": {
        "erc20": "fixture/abis/CentipedeERC20.json",
        "erc1155": "fixture/abis/CentipedeERC1155.json",
        "erc721": "fixture/abis/CentipedeERC721.json",
    },
    "bytecode": {
        "erc20": "fixture/bytecodes/CentipedeERC20.bin",
        "erc1155": "fixture/bytecodes/CentipedeERC1155.bin",
        "erc721": "fixture/bytecodes/CentipedeERC721.bin",
    },
}


class CentipedeContract:
    def __init__(self, abi_path: str, bytecode_path: str) -> None:
        self._abi_path = abi_path
        self._bytecode_path = bytecode_path

    def abi(self) -> Dict[str, Any]:
        base_dir = os.path.dirname(__file__)
        with open(os.path.join(base_dir, self._abi_path), "r") as ifp:
            abi = json.load(ifp)
        return abi

    def bytecode(self) -> str:
        base_dir = os.path.dirname(__file__)
        with open(os.path.join(base_dir, self._bytecode_path), "r") as ifp:
            bytecode = ifp.read()
        return bytecode


ERC20 = CentipedeContract(_PATHS["abi"]["erc20"], _PATHS["bytecode"]["erc20"])
ERC721 = CentipedeContract(_PATHS["abi"]["erc721"], _PATHS["bytecode"]["erc721"])
ERC1155 = CentipedeContract(_PATHS["abi"]["erc1155"], _PATHS["bytecode"]["erc1155"])

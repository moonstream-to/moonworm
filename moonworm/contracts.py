import json
import os
from typing import Any, Dict, List

_PATHS = {
    "abi": {
        "erc20": "fixture/abis/OwnableERC20.json",
        "erc1155": "fixture/abis/OwnableERC1155.json",
        "erc721": "fixture/abis/OwnableERC721.json",
        "cu": "fixture/abis/CUContract.json",
        "cu_land": "fixture/abis/CULands.json",
    },
    "bytecode": {
        "erc20": "fixture/bytecodes/OwnableERC20.bin",
        "erc1155": "fixture/bytecodes/OwnableERC1155.bin",
        "erc721": "fixture/bytecodes/OwnableERC721.bin",
    },
}


class MoonwormContract:
    def __init__(self, abi_path: str, bytecode_path: str) -> None:
        self._abi_path = abi_path
        self._bytecode_path = bytecode_path

    def abi(self) -> List[Dict[str, Any]]:
        base_dir = os.path.dirname(__file__)
        with open(os.path.join(base_dir, self._abi_path), "r") as ifp:
            abi = json.load(ifp)
        return abi

    def bytecode(self) -> str:
        base_dir = os.path.dirname(__file__)
        with open(os.path.join(base_dir, self._bytecode_path), "r") as ifp:
            bytecode = ifp.read()
        return bytecode


ERC20 = MoonwormContract(_PATHS["abi"]["erc20"], _PATHS["bytecode"]["erc20"])
ERC721 = MoonwormContract(_PATHS["abi"]["erc721"], _PATHS["bytecode"]["erc721"])
ERC1155 = MoonwormContract(_PATHS["abi"]["erc1155"], _PATHS["bytecode"]["erc1155"])
CU = MoonwormContract(_PATHS["abi"]["cu"], "")
CULands = MoonwormContract(_PATHS["abi"]["cu_land"], "")

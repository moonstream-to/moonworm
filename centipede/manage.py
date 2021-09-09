import json
from hexbytes.main import HexBytes

from web3 import Web3
from .generator import generate_contract_file

f = open("centipede/abi.json")
abi = json.load(f)
IPC_PATH = "http://127.0.0.1:18375"


w3 = Web3(Web3.HTTPProvider(IPC_PATH))
contract = w3.eth.contract(
    abi=abi, address=w3.toChecksumAddress("0x06012c8cf97bead5deae237070f9587f8e7a266d")
)
print(type(contract.functions.getKitty(1).call()))

generate_contract_file("0x06012c8cf97bead5deae237070f9587f8e7a266d", abi)

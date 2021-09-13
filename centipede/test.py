import json
from typing import Any, Dict, Union

from eth_typing.evm import Address, ChecksumAddress
from web3 import Web3

CONTRACT_ADDRESS = "0x06012c8cf97bead5deae237070f9587f8e7a266d"

with open("abi.json", "r") as abi_file:
    CONTRACT_ABI = json.load(abi_file)


class Contract:
    # GET CONTRACT ADDRESS IN INIT
    def __init__(self, web3: Web3):
        self.web3 = web3

        self.contract = web3.eth.contract(
            address=web3.toChecksumAddress(CONTRACT_ADDRESS), abi=CONTRACT_ABI
        )

    def supportsInterface(self, _interfaceID: bytes) -> Any:
        return self.contract.functions.supportsInterface(_interfaceID).call()

    def cfoAddress(self) -> Any:
        return self.contract.functions.cfoAddress().call()

    def tokenMetadata(self, _tokenId: int, _preferredTransport: str) -> Any:
        return self.contract.functions.tokenMetadata(
            _tokenId, _preferredTransport
        ).call()

    def promoCreatedCount(self) -> Any:
        return self.contract.functions.promoCreatedCount().call()

    def name(self) -> Any:
        return self.contract.functions.name().call()

    def approve(self, _to: Union[Address, ChecksumAddress], _tokenId: int) -> Any:
        return self.contract.functions.approve(_to, _tokenId).call()

    def ceoAddress(self) -> Any:
        return self.contract.functions.ceoAddress().call()

    def GEN0_STARTING_PRICE(self) -> Any:
        return self.contract.functions.GEN0_STARTING_PRICE().call()

    def setSiringAuctionAddress(self, _address: Union[Address, ChecksumAddress]) -> Any:
        return self.contract.functions.setSiringAuctionAddress(_address).call()

    def totalSupply(self) -> Any:
        return self.contract.functions.totalSupply().call()

    def pregnantKitties(self) -> Any:
        return self.contract.functions.pregnantKitties().call()

    def isPregnant(self, _kittyId: int) -> Any:
        return self.contract.functions.isPregnant(_kittyId).call()

    def GEN0_AUCTION_DURATION(self) -> Any:
        return self.contract.functions.GEN0_AUCTION_DURATION().call()

    def siringAuction(self) -> Any:
        return self.contract.functions.siringAuction().call()

    def transferFrom(
        self,
        _from: Union[Address, ChecksumAddress],
        _to: Union[Address, ChecksumAddress],
        _tokenId: int,
    ) -> Any:
        return self.contract.functions.transferFrom(_from, _to, _tokenId).call()

    def setGeneScienceAddress(self, _address: Union[Address, ChecksumAddress]) -> Any:
        return self.contract.functions.setGeneScienceAddress(_address).call()

    def setCEO(self, _newCEO: Union[Address, ChecksumAddress]) -> Any:
        return self.contract.functions.setCEO(_newCEO).call()

    def setCOO(self, _newCOO: Union[Address, ChecksumAddress]) -> Any:
        return self.contract.functions.setCOO(_newCOO).call()

    def createSaleAuction(
        self, _kittyId: int, _startingPrice: int, _endingPrice: int, _duration: int
    ) -> Any:
        return self.contract.functions.createSaleAuction(
            _kittyId, _startingPrice, _endingPrice, _duration
        ).call()

    def unpause(self) -> Any:
        return self.contract.functions.unpause().call()

    def sireAllowedToAddress(self, arg1: int) -> Any:
        return self.contract.functions.sireAllowedToAddress(arg1).call()

    def canBreedWith(self, _matronId: int, _sireId: int) -> Any:
        return self.contract.functions.canBreedWith(_matronId, _sireId).call()

    def kittyIndexToApproved(self, arg1: int) -> Any:
        return self.contract.functions.kittyIndexToApproved(arg1).call()

    def createSiringAuction(
        self, _kittyId: int, _startingPrice: int, _endingPrice: int, _duration: int
    ) -> Any:
        return self.contract.functions.createSiringAuction(
            _kittyId, _startingPrice, _endingPrice, _duration
        ).call()

    def setAutoBirthFee(self, val: int) -> Any:
        return self.contract.functions.setAutoBirthFee(val).call()

    def approveSiring(
        self, _addr: Union[Address, ChecksumAddress], _sireId: int
    ) -> Any:
        return self.contract.functions.approveSiring(_addr, _sireId).call()

    def setCFO(self, _newCFO: Union[Address, ChecksumAddress]) -> Any:
        return self.contract.functions.setCFO(_newCFO).call()

    def createPromoKitty(
        self, _genes: int, _owner: Union[Address, ChecksumAddress]
    ) -> Any:
        return self.contract.functions.createPromoKitty(_genes, _owner).call()

    def setSecondsPerBlock(self, secs: int) -> Any:
        return self.contract.functions.setSecondsPerBlock(secs).call()

    def paused(self) -> Any:
        return self.contract.functions.paused().call()

    def withdrawBalance(self) -> Any:
        return self.contract.functions.withdrawBalance().call()

    def ownerOf(self, _tokenId: int) -> Any:
        return self.contract.functions.ownerOf(_tokenId).call()

    def GEN0_CREATION_LIMIT(self) -> Any:
        return self.contract.functions.GEN0_CREATION_LIMIT().call()

    def newContractAddress(self) -> Any:
        return self.contract.functions.newContractAddress().call()

    def setSaleAuctionAddress(self, _address: Union[Address, ChecksumAddress]) -> Any:
        return self.contract.functions.setSaleAuctionAddress(_address).call()

    def balanceOf(self, _owner: Union[Address, ChecksumAddress]) -> Any:
        return self.contract.functions.balanceOf(_owner).call()

    def setNewAddress(self, _v2Address: Union[Address, ChecksumAddress]) -> Any:
        return self.contract.functions.setNewAddress(_v2Address).call()

    def secondsPerBlock(self) -> Any:
        return self.contract.functions.secondsPerBlock().call()

    def pause(self) -> Any:
        return self.contract.functions.pause().call()

    def tokensOfOwner(self, _owner: Union[Address, ChecksumAddress]) -> Any:
        return self.contract.functions.tokensOfOwner(_owner).call()

    def giveBirth(self, _matronId: int) -> Any:
        return self.contract.functions.giveBirth(_matronId).call()

    def withdrawAuctionBalances(self) -> Any:
        return self.contract.functions.withdrawAuctionBalances().call()

    def symbol(self) -> Any:
        return self.contract.functions.symbol().call()

    def cooldowns(self, arg1: int) -> Any:
        return self.contract.functions.cooldowns(arg1).call()

    def kittyIndexToOwner(self, arg1: int) -> Any:
        return self.contract.functions.kittyIndexToOwner(arg1).call()

    def transfer(self, _to: Union[Address, ChecksumAddress], _tokenId: int) -> Any:
        return self.contract.functions.transfer(_to, _tokenId).call()

    def cooAddress(self) -> Any:
        return self.contract.functions.cooAddress().call()

    def autoBirthFee(self) -> Any:
        return self.contract.functions.autoBirthFee().call()

    def erc721Metadata(self) -> Any:
        return self.contract.functions.erc721Metadata().call()

    def createGen0Auction(self, _genes: int) -> Any:
        return self.contract.functions.createGen0Auction(_genes).call()

    def isReadyToBreed(self, _kittyId: int) -> Any:
        return self.contract.functions.isReadyToBreed(_kittyId).call()

    def PROMO_CREATION_LIMIT(self) -> Any:
        return self.contract.functions.PROMO_CREATION_LIMIT().call()

    def setMetadataAddress(
        self, _contractAddress: Union[Address, ChecksumAddress]
    ) -> Any:
        return self.contract.functions.setMetadataAddress(_contractAddress).call()

    def saleAuction(self) -> Any:
        return self.contract.functions.saleAuction().call()

    def getKitty(self, _id: int) -> Any:
        return self.contract.functions.getKitty(_id).call()

    def bidOnSiringAuction(self, _sireId: int, _matronId: int) -> Any:
        return self.contract.functions.bidOnSiringAuction(_sireId, _matronId).call()

    def gen0CreatedCount(self) -> Any:
        return self.contract.functions.gen0CreatedCount().call()

    def geneScience(self) -> Any:
        return self.contract.functions.geneScience().call()

    def breedWithAuto(self, _matronId: int, _sireId: int) -> Any:
        return self.contract.functions.breedWithAuto(_matronId, _sireId).call()


IPC_PATH = "http://127.0.0.1:18375"


w3 = Web3(Web3.HTTPProvider(IPC_PATH))
cryptoKitties = Contract(w3)


print(cryptoKitties.ownerOf(1))
print(cryptoKitties.getKitty(1))
print(cryptoKitties.kittyIndexToApproved(1))

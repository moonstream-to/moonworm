///@notice This contract follows ERC20, only owner can mint new tokens
// SPDX-License-Identifier: GPL-2.0
pragma solidity ^0.8.0;

import "./openzeppelin-contracts/contracts/token/ERC721/ERC721.sol";
import "./openzeppelin-contracts/contracts/access/Ownable.sol";

contract OwnableERC721 is ERC721, Ownable {
    constructor(
        string memory name_,
        string memory symbol_,
        address owner
    ) ERC721(name_, symbol_) {
        transferOwnership(owner);
    }

    function mint(address to, uint256 tokenId) public onlyOwner {
        _safeMint(to, tokenId);
    }
}

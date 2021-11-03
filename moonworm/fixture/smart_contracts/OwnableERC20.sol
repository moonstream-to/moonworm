///@notice This contract follows ERC20, only owner can mint new tokens
// SPDX-License-Identifier: GPL-2.0
pragma solidity ^0.8.0;

import "./openzeppelin-contracts/contracts/token/ERC20/ERC20.sol";
import "./openzeppelin-contracts/contracts/access/Ownable.sol";

contract OwnableERC20 is ERC20, Ownable {
    constructor(
        string memory name_,
        string memory symbol_,
        address owner
    ) ERC20(name_, symbol_) {
        transferOwnership(owner);
    }

    function mint(address account, uint256 amount) public onlyOwner {
        _mint(account, amount);
    }

    function decimals() public view virtual override returns (uint8) {
        return 0;
    }
}

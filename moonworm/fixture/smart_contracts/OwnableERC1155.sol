///@notice This contract follows ERC1155, only owner can create and mint token
// SPDX-License-Identifier: GPL-2.0

pragma solidity ^0.8.0;
import "./openzeppelin-contracts/contracts/token/ERC1155/ERC1155.sol";
import "./openzeppelin-contracts/contracts/access/Ownable.sol";
import "./openzeppelin-contracts/contracts/utils/Counters.sol";

contract OwnableERC1155 is ERC1155, Ownable {
    using Counters for Counters.Counter;
    Counters.Counter private ID;

    bool public paused = false;
    string public name;
    string public symbol;

    // Mapping from token ID to token URI
    mapping(uint256 => string) private idToUri;

    // Mapping from token ID to token supply
    mapping(uint256 => uint256) private tokenSupply;

    constructor(
        string memory _name,
        string memory _symbol,
        string memory _uri,
        address owner
    ) ERC1155(_uri) {
        name = _name;
        symbol = _symbol;

        transferOwnership(owner);
    }

    modifier pausable() {
        if (paused) {
            revert("Paused");
        } else {
            _;
        }
    }

    /**
     * @dev Creates a new NFT type
     * @param _cid Content identifier
     * @param _data Data to pass if receiver is contract
     * @return _id The newly created token ID
     */
    function create(string calldata _cid, bytes calldata _data)
        external
        onlyOwner
        returns (uint256 _id)
    {
        require(bytes(_cid).length > 0, "Err: Missing Content Identifier");

        _id = _nextId();

        _mint(msg.sender, _id, 0, _data);

        string memory _uri = _createUri(_cid);
        idToUri[_id] = _uri;

        emit URI(_uri, _id);
    }

    /**
     * @dev Mints an existing NFT type
     * @notice Enforces a maximum of 1 minting event per NFT type per account
     * @param _account Account to mint NFT to (i.e. the owner)
     * @param _id ID (i.e. type) of  NFT to mint
     * // _signature Verified signature granting _account an NFT
     * @param _data Data to pass if receiver is contract
     */
    function mint(
        address _account,
        uint256 _id,
        uint256 _amount,
        bytes calldata _data
    ) public pausable onlyOwner {
        require(_exists(_id), "Err: Invalid ID");
        //require(verify(_account, _id, _signature), "Err: Invalid Signature");

        _mint(_account, _id, _amount, _data);

        tokenSupply[_id] += _amount;
    }

    /**
     * @dev Batch mints multiple different existing NFT types
     * @notice Enforces a maximum of 1 minting event per account per NFT type
     * @param _account Account to mint NFT to (i.e. the owner)
     * @param _ids IDs of the type of NFT to mint
     * @param _data Data to pass if receiver is contract
     */
    function batchMint(
        address _account,
        uint256[] calldata _ids,
        uint256 _amount,
        bytes[] calldata _data
    ) external pausable onlyOwner {
        for (uint256 i = 0; i < _ids.length; i++) {
            mint(_account, _ids[i], _amount, _data[i]);
        }
    }

    function _createUri(string memory _cid)
        internal
        view
        returns (string memory _uri)
    {
        string memory baseUri = super.uri(0);
        return string(abi.encodePacked(baseUri, _cid));
    }

    function _nextId() internal returns (uint256 id) {
        ID.increment();
        return ID.current();
    }

    function _exists(uint256 _id) internal view returns (bool) {
        return (bytes(idToUri[_id]).length > 0);
    }

    /**
     * @dev Returns the uri of a token given its ID
     * @param _id ID of the token to query
     * @return uri of the token or an empty string if it does not exist
     */
    function uri(uint256 _id) public view override returns (string memory) {
        return idToUri[_id];
    }

    /**
     * @dev Returns the total quantity for a token ID
     * @param _id ID of the token to query
     * @return amount of token in existence
     */
    function totalSupply(uint256 _id) public view returns (uint256) {
        return tokenSupply[_id];
    }

    /**
     * @dev Pause or unpause the minting and creation of NFTs
     */
    function pause() public onlyOwner {
        paused = !paused;
    }
}

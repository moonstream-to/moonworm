pragma solidity >0.5.0;

contract Greeter {
    string public greeting;

    constructor() {
        greeting = "Hello";
    }

    function setGreeting(string memory _greeting)
        public
        returns (string memory)
    {
        greeting = _greeting;
        return greeting;
    }

    function greet() public view returns (string memory) {
        return greeting;
    }

    function pr_greet() private view returns (string memory) {
        return greeting;
    }
}

 pragma solidity >0.5.0;

    contract Greeter {
        string public greeting;

        constructor() public {
            greeting = 'Hello';
        }

        function setGreeting(string memory _greeting) public returns (string memory){
                greeting = _greeting;
                return greeting;
        }

        function greet() view public returns (string memory) {
            return greeting;
        }
        function pr_greet() view private returns (string memory) {
            return greeting;
        }
    }
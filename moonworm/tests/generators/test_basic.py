import unittest

from moonworm.generators.basic import function_spec


class TestFunctionSpec(unittest.TestCase):
    def test_function_spec_single_input(self):
        function_abi = {
            "inputs": [
                {"internalType": "uint256", "name": "_tokenId", "type": "uint256"}
            ],
            "name": "getDNA",
            "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
            "stateMutability": "view",
            "type": "function",
        }
        expected_spec = {
            "abi": "getDNA",
            "method": "get_dna",
            "cli": "get-dna",
            "inputs": [
                {
                    "abi": "_tokenId",
                    "method": "_token_id",
                    "cli": "--token-id-arg",
                    "args": "token_id_arg",
                    "type": "int",
                    "cli_type": "int",
                },
            ],
            "transact": False,
        }
        spec = function_spec(function_abi)
        self.assertDictEqual(spec, expected_spec)

    def test_function_spec_multiple_inputs(self):
        function_abi = {
            "inputs": [
                {"internalType": "address", "name": "owner", "type": "address"},
                {"internalType": "uint256", "name": "index", "type": "uint256"},
            ],
            "name": "tokenOfOwnerByIndex",
            "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
            "stateMutability": "view",
            "type": "function",
        }
        expected_spec = {
            "abi": "tokenOfOwnerByIndex",
            "method": "token_of_owner_by_index",
            "cli": "token-of-owner-by-index",
            "inputs": [
                {
                    "abi": "owner",
                    "method": "owner",
                    "cli": "--owner",
                    "args": "owner",
                    "type": "ChecksumAddress",
                    "cli_type": None,
                },
                {
                    "abi": "index",
                    "method": "index",
                    "cli": "--index",
                    "args": "index",
                    "type": "int",
                    "cli_type": "int",
                },
            ],
            "transact": False,
        }
        spec = function_spec(function_abi)
        self.assertDictEqual(spec, expected_spec)


if __name__ == "__main__":
    unittest.main()

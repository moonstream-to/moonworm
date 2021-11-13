import os
import tempfile
import unittest

from hexbytes.main import HexBytes
from web3 import Web3

from moonworm.contracts import ERC1155

from ...crawler.function_call_crawler import (
    FunctionCallCrawler,
    PickleFileState,
    Web3StateProvider,
)
from ...web3_util import connect


def get_web3_provider():
    provider_path = os.environ.get("MOONWORM_MAINNET_PROVIDER_PATH")
    if provider_path is None:
        raise Exception("MOONWORM_MAINNET_PROVIDER_PATH environment variable not set")
    return connect(provider_path)


class FunctionCrawlerTestnetTestCase(unittest.TestCase):
    def setUp(self):
        try:
            self.web3 = get_web3_provider()
        except Exception as e:
            raise unittest.SkipTest(f"Skipping test because of : {str(e)}")
        self.crawldir = tempfile.mkdtemp()
        self.pickle_file = os.path.join(self.crawldir, "state.pkl")
        self.crawler_state = PickleFileState(self.pickle_file)

    def test_crawl(self):
        start_block = 13570810
        end_block = 13570810
        crawler = FunctionCallCrawler(
            self.crawler_state,
            Web3StateProvider(self.web3),
            ERC1155.abi(),
            contract_addresses=[
                Web3.toChecksumAddress("0x495f947276749ce646f68ac8c248420045cb7b5e"),
            ],
        )
        crawler.crawl(start_block, end_block)

        expected_call = {
            "block_number": 13570810,
            "block_timestamp": 1636307634,
            "transaction_hash": HexBytes(
                "0xd9d3e5a1824520b2ec81b5535ec6fed55eaeb53803cc626f12d088c2149655e7"
            ),
            "contract_address": "0x495f947276749Ce646f68AC8c248420045cb7b5e",
            "caller_address": "0xeA8Bf027d2665D62f12e749186B3a7860877C574",
            "function_name": "safeTransferFrom",
            "function_args": {
                "from": "0xeA8Bf027d2665D62f12e749186B3a7860877C574",
                "to": "0x7b340Bc86c3Ed919b473c51b584e82bD11d4a9D1",
                "id": 106088455803207371738270406628853896761625078047250982059471653436723076005889,
                "amount": 1,
                "data": b"",
            },
        }

        self.assertEqual(len(crawler.state.state["calls"]), 1)
        self.assertEqual(crawler.state.state["calls"][0], expected_call)


if __name__ == "__main__":
    unittest.main()

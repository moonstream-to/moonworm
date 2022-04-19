"""
This module allows users to inspect the conditions under which a smart contract was deployed.
"""
import logging
import os
import time
from typing import Dict, Optional

from eth_typing.evm import ChecksumAddress
from web3 import Web3

CONFIG_KEY_WEB3_INTERVAL = "web3_interval"
CONFIG_KEY_WEB3_LAST_CALL = "web3_last_call"

logger = logging.getLogger("moonworm.deployment")
VERBOSE = os.environ.get("MOONWORM_VERBOSE", "f").lower() in {
    "y",
    "yes",
    "t",
    "true",
    "1",
}
logger.setLevel(logging.INFO if VERBOSE else logging.WARNING)


def was_deployed_at_block(
    web3_client: Web3,
    contract_address: ChecksumAddress,
    block_number: int,
    config: Optional[Dict[str, float]],
) -> bool:
    if config is not None:
        interval = config.get(CONFIG_KEY_WEB3_INTERVAL)
        if interval is not None:
            last_call = config.get(CONFIG_KEY_WEB3_LAST_CALL)
            current_time = time.time()
            if last_call is not None and current_time < last_call + interval:
                time.sleep(last_call + interval - current_time + 1)

    code = web3_client.eth.get_code(contract_address, block_identifier=block_number)

    if config is not None:
        config[CONFIG_KEY_WEB3_LAST_CALL] = time.time()

    code_hex = code.hex()
    was_deployed = not (code_hex == "0x" or code_hex == "0x0" or code_hex == "")
    return was_deployed


def find_deployment_block(
    web3_client: Web3,
    contract_address: ChecksumAddress,
    web3_interval: float,
) -> Optional[int]:
    """
    Note: We will assume no selfdestruct for now.

    This means that, if the address does not currently contain code, we will assume it never contained
    code and is therefore not a smart contract address.
    """
    log_prefix = f"find_deployment_block(web3_client, contract_address={contract_address}, web3_interval={web3_interval}) -- "

    logger.info(f"{log_prefix}Function invoked")
    config = {CONFIG_KEY_WEB3_INTERVAL: web3_interval}

    max_block = int(web3_client.eth.block_number)
    min_block = 0
    middle_block = int((min_block + max_block) / 2)

    was_deployed_at_max_block = was_deployed_at_block(
        web3_client, contract_address, max_block, config=config
    )
    if not was_deployed_at_max_block:
        logger.warn(f"{log_prefix}Address is not a smart contract")
        return None

    was_deployed: Dict[int, bool] = {
        max_block: was_deployed_at_max_block,
        min_block: was_deployed_at_block(
            web3_client, contract_address, min_block, config=config
        ),
        middle_block: was_deployed_at_block(
            web3_client, contract_address, middle_block, config=config
        ),
    }

    while max_block - min_block >= 2:
        logger.info(
            f"{log_prefix}Binary search -- max_block={max_block}, min_block={min_block}, middle_block={middle_block}"
        )
        if not was_deployed[min_block] and not was_deployed[middle_block]:
            min_block = middle_block
        else:
            max_block = middle_block

        middle_block = int((min_block + max_block) / 2)

        was_deployed[middle_block] = was_deployed_at_block(
            web3_client, contract_address, middle_block, config=config
        )

    if was_deployed[min_block]:
        return min_block
    return max_block

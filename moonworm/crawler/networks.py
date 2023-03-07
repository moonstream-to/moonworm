from typing import Dict

try:
    from moonstreamdb.db import yield_db_session_ctx
    from moonstreamdb.models import (
        EthereumBlock,
        EthereumLabel,
    )  # state/moonstream_event_state dependency maybe removed in the future
    from moonstreamdb.networks import MODELS, Network, tx_raw_types

except ImportError:
    print("this feature requires moonstreamdb which is not installed")
    print("to enable, run: `pip install moonworm[moonstream]`")
    raise ImportError(
        "moonstreamdb not installed, to install, run: `pip install moonworm[moonstream]`"
    )

from typing import Dict

try:
    from moonstreamdb.db import yield_db_session_ctx
    from moonstreamdb.models import (  # state/moonstream_event_state dependency maybe removed in the future
        EthereumBlock,
        EthereumLabel,
    )
    from moonstreamtypes.networks import MODELS, Network, tx_raw_types, MODELS_V3

except ImportError:
    print("this feature requires moonstreamdb which is not installed")
    print("to enable, run: `pip install moonworm[moonstream]`")
    raise ImportError(
        "moonstreamdb not installed, to install, run: `pip install moonworm[moonstream]`"
    )

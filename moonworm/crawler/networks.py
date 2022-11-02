from typing import Dict

try:
    from moonstreamdb.db import yield_db_session_ctx
    from moonstreamdb.models import (
        Base,
        EthereumBlock,
        EthereumLabel,
        EthereumTransaction,
        MumbaiBlock,
        MumbaiLabel,
        MumbaiTransaction,
        PolygonBlock,
        PolygonLabel,
        PolygonTransaction,
        XDaiBlock,
        XDaiLabel,
        XDaiTransaction,
    )
except ImportError:
    print("this feature requires moonstreamdb which is not installed")
    print("to enable, run: `pip install moonworm[moonstream]`")
    raise ImportError(
        "moonstreamdb not installed, to install, run: `pip install moonworm[moonstream]`"
    )


from .utils import Network

MODELS: Dict[Network, Dict[str, Base]] = {
    Network.ethereum: {
        "blocks": EthereumBlock,
        "labels": EthereumLabel,
        "transactions": EthereumTransaction,
    },
    Network.mumbai: {
        "blocks": MumbaiBlock,
        "labels": MumbaiLabel,
        "transactions": MumbaiTransaction,
    },
    Network.polygon: {
        "blocks": PolygonBlock,
        "labels": PolygonLabel,
        "transactions": PolygonTransaction,
    },
    Network.xdai: {
        "blocks": XDaiBlock,
        "labels": XDaiLabel,
        "transactions": XDaiTransaction,
    },
}

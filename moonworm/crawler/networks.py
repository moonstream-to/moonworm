from enum import Enum
from typing import Dict

from moonstreamdb.models import (
    Base,
    EthereumBlock,
    EthereumLabel,
    EthereumTransaction,
    PolygonBlock,
    PolygonLabel,
    PolygonTransaction,
    XDaiBlock,
    XDaiLabel,
    XDaiTransaction,
)


class Network(Enum):
    ethereum = "ethereum"
    polygon = "polygon"
    xdai = "xdai"


MODELS: Dict[Network, Dict[str, Base]] = {
    Network.ethereum: {
        "blocks": EthereumBlock,
        "labels": EthereumLabel,
        "transactions": EthereumTransaction,
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

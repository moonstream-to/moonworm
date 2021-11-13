from moonstreamdb.models import EthereumBlock, EthereumLabel
from sqlalchemy.orm import Query, Session
from web3 import Web3

from .event_scanner_state import EventScannerState

BLOCK_TIMESTAMP_CACHE = {}


def get_block_timestamp(db_session: Session, web3: Web3, block_number: int) -> int:
    """
    Get the timestamp of a block.
    """
    if block_number in BLOCK_TIMESTAMP_CACHE:
        return BLOCK_TIMESTAMP_CACHE[block_number]
    try:
        block = (
            db_session.query(EthereumBlock)
            .filter(EthereumBlock.block_number == block_number)
            .query.one()
        )
        if block is None:
            raise ValueError("Block not found is db")
        timstamp = block.timestamp
    except Exception as e:
        print(e)
        timestamp = web3.eth.get_block(block_number)["timestamp"]

    # clear cache if size is > 100
    if len(BLOCK_TIMESTAMP_CACHE) > 100:
        BLOCK_TIMESTAMP_CACHE.clear()

    BLOCK_TIMESTAMP_CACHE[block_number] = timestamp
    return timestamp


class MoonStreamEventState(EventScannerState):
    """
    MoonStream event state.
    """

    def __init__(self, db_session: Session, web3: Web3, label_name: str):
        self.db_session = db_session
        self.web3 = web3
        self.label_name = label_name

        self.cache_state = []

    def get_last_scanned_block(self) -> int:
        last = (
            self.db_session.query(EthereumLabel)
            .filter(EthereumLabel.label_name == self.label_name)
            .order_by(EthereumLabel.block_number.desc())
            .first()
        )
        if last is None:
            return 0
        return last.block_number

    def start_chunck() -> None:
        pass

    def delete_data(self, since_block: int):
        to_delete = self.db_session.query(EthereumLabel).filter(
            EthereumLabel.label_name == self.label_name,
            EthereumLabel.block_number >= since_block,
        )
        to_delete.delete()
        try:
            self.db_session.commit()
        except Exception as e:
            print(e)
            self.db_session.rollback()

    def process_event(self, event: dict) -> None:
        """
        Process an event.
        """
        block_number = event["blockNumber"]
        timestamp = get_block_timestamp(self.db_session, self.web3, block_number)
        label = EthereumLabel(
            label_name=self.label_name,
            block_number=block_number,
            timestamp=timestamp,
            event=event,
        )

        self.cache_state.append(label)

    def flush_state(self) -> None:
        """
        Flush the state to the database.
        """
        if not self.cache_state:
            return

        try:
            self.db_session.add_all(self.cache_state)
            self.db_session.commit()

        except Exception as e:
            print(e)
            self.db_session.rollback()
        self.cache_state = []

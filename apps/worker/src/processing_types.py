from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class QueueMessage:
    message_id: str
    fields: dict[str, str]


class ProcessingOutcome(Enum):
    ACKNOWLEDGED = "acknowledged"
    DEAD_LETTERED = "dead_lettered"
    RETRY_PENDING = "retry_pending"


class StorageError(Exception):
    """A persistence operation failed; the caller must not finalize separately."""


class InvalidCheckpointError(Exception):
    def __init__(self, raw_completion: str):
        super().__init__("Stored completion is invalid")
        self.raw_completion = raw_completion

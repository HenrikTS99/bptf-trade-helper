from enum import Enum
from dataclasses import dataclass


class SyncPhase(Enum):
    IDLE = "idle"
    SCANNING = "scanning"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class SyncTracker:
    phase: SyncPhase = SyncPhase.IDLE
    current: int = 0
    total: int = 0
    message: str = ""

    @property
    def is_syncing(self) -> bool:
        return self.phase == SyncPhase.SCANNING

    def start(self):
        self.phase = SyncPhase.SCANNING
        self.current = 0
        self.total = 0
        self.message = "Starting..."

    def update_progress(self, current: int, total: int):
        self.current = current
        self.total = total
        self.message = f"Refreshing buy states... ({current}/{total})"

    def complete(self, elapsed: float):
        self.phase = SyncPhase.COMPLETED
        self.message = f"Done in {elapsed:.0f}s"

    def fail(self, error: str):
        self.phase = SyncPhase.FAILED
        self.message = str(error)


sync_tracker = SyncTracker()

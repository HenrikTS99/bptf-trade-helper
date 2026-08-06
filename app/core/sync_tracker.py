from dataclasses import dataclass, field
from enum import Enum

from app.models.enums import Intent


class SyncPhase(Enum):
    IDLE = "idle"
    SCANNING = "scanning"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class SyncTracker:
    intent: Intent
    phase: SyncPhase = SyncPhase.IDLE
    current: int = 0
    total: int = 0
    message: str = ""
    synced_ids: list[str] = field(default_factory=list)

    @property
    def is_syncing(self) -> bool:
        return self.phase == SyncPhase.SCANNING

    def start(self):
        self.phase = SyncPhase.SCANNING
        self.current = 0
        self.total = 0
        self.message = "Starting..."
        self.synced_ids.clear()

    def update_progress(self, current: int, total: int):
        self.current = current
        self.total = total
        self.message = f"Refreshing {self.intent} states... ({current}/{total})"

    def complete(self, elapsed: float):
        self.phase = SyncPhase.COMPLETED
        self.message = f"Done in {elapsed:.0f}s"

    def fail(self, error: str):
        self.phase = SyncPhase.FAILED
        self.message = str(error)


buy_sync_tracker = SyncTracker(intent=Intent.buy)
sell_sync_tracker = SyncTracker(intent=Intent.sell)

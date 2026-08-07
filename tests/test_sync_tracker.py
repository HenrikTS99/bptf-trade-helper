from app.core.sync_tracker import SyncPhase, SyncTracker
from app.models.enums import Intent


def test_initial_state():
    t = SyncTracker(intent=Intent.buy)
    assert t.phase == SyncPhase.IDLE
    assert t.current == 0 and t.total == 0
    assert t.message == ""
    assert t.synced_ids == []
    assert not t.is_syncing


def test_start():
    t = SyncTracker(intent=Intent.buy)
    t.synced_ids.append("x")
    t.start()
    assert t.phase == SyncPhase.SCANNING
    assert t.is_syncing
    assert t.current == 0 and t.total == 0
    assert t.message == "Starting..."
    assert t.synced_ids == []


def test_update_progress():
    t = SyncTracker(intent=Intent.sell)
    t.update_progress(3, 10)
    assert t.current == 3 and t.total == 10
    assert t.message == "Refreshing sell states... (3/10)"


def test_complete():
    t = SyncTracker(intent=Intent.buy)
    t.complete(5.2)
    assert t.phase == SyncPhase.COMPLETED
    assert t.message == "Done in 5s"


def test_fail():
    t = SyncTracker(intent=Intent.buy)
    t.fail("backend unreachable")
    assert t.phase == SyncPhase.FAILED
    assert t.message == "backend unreachable"

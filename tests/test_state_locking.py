from multiprocessing import Process
from pathlib import Path

from data_curator_app import curator_core as core


def _worker_update(repo: str, fname: str, status: str):
    # Child process entry: perform an update on a unique filename
    core.update_file_status(repo, fname, status)


def test_concurrent_writers_preserve_all_updates(tmp_path: Path):
    repo = tmp_path
    # Launch several concurrent writers updating distinct files
    procs = []
    for i in range(8):
        p = Process(
            target=_worker_update,
            args=(str(repo), f"f{i}.txt", "keep_forever" if i % 2 else "decide_later"),
        )
        procs.append(p)

    # Start near-simultaneously
    for p in procs:
        p.start()
    for p in procs:
        p.join(timeout=10)

    # All processes should have completed
    assert all(p.exitcode == 0 for p in procs)

    # State should contain all distinct entries without being clobbered
    state = core.load_state(str(repo))
    # Exclude reserved keys
    file_keys = [k for k in state.keys() if not str(k).startswith("_")]
    assert len(file_keys) == 8
    for i in range(8):
        assert f"f{i}.txt" in file_keys


def test_lockfile_created_and_reused(tmp_path: Path):
    repo = tmp_path
    # First write creates lockfile implicitly
    core.update_file_status(str(repo), "a.txt", "keep_forever")
    lockfile = repo / f"{core.STATE_FILENAME}.lock"
    assert lockfile.exists()

    # A second write should succeed and not hang
    core.update_file_status(str(repo), "b.txt", "decide_later")
    state = core.load_state(str(repo))
    file_keys = {k for k in state.keys() if not str(k).startswith("_")}
    assert file_keys == {"a.txt", "b.txt"}

import pytest

from ci_hunter.file_lock import locked_file


def test_locked_file_raises_on_timeout(tmp_path, monkeypatch):
    target = tmp_path / "queue.jsonl"

    def always_block(_handle, _length):
        raise BlockingIOError

    import ci_hunter.file_lock as file_lock

    monkeypatch.setattr(file_lock, "_try_lock", always_block)

    with pytest.raises(RuntimeError, match="timed out"):
        with locked_file(target, "a", timeout_seconds=0.01, poll_interval=0.0):
            pass


def test_locked_file_writes_when_available(tmp_path):
    target = tmp_path / "queue.jsonl"

    with locked_file(target, "a"):
        pass

    assert target.exists()


def test_locked_file_raises_when_no_backend(tmp_path, monkeypatch):
    target = tmp_path / "queue.jsonl"

    import ci_hunter.file_lock as file_lock

    monkeypatch.setattr(file_lock, "fcntl", None)
    monkeypatch.setattr(file_lock, "msvcrt", None)

    with pytest.raises(RuntimeError, match="locking backend"):
        with locked_file(target, "a", timeout_seconds=0.01, poll_interval=0.0):
            pass


def test_lock_length_is_at_least_one(tmp_path):
    target = tmp_path / "queue.jsonl"
    target.write_text("abc", encoding="utf-8")

    import ci_hunter.file_lock as file_lock

    assert file_lock._lock_length(target) == 3

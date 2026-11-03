"""An advisory output-folder lock shared by the CLI and desktop monitor."""

from contextlib import contextmanager
from pathlib import Path
import os


def _lock(file):
    file.seek(0)
    if os.name == "nt":
        import msvcrt
        msvcrt.locking(file.fileno(), msvcrt.LK_NBLCK, 1)
    else:
        import fcntl
        fcntl.flock(file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


def _unlock(file):
    file.seek(0)
    if os.name == "nt":
        import msvcrt
        msvcrt.locking(file.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl
        fcntl.flock(file.fileno(), fcntl.LOCK_UN)


def batch_is_running(output):
    path = Path(output) / ".charm-batch.lock"
    if not path.exists():
        return False
    with path.open("r+b") as file:
        try:
            _lock(file)
        except OSError:
            return True
        _unlock(file)
    return False


@contextmanager
def batch_lock(output):
    with (Path(output) / ".charm-batch.lock").open("a+b") as file:
        if file.seek(0, os.SEEK_END) == 0:
            file.write(b"0")
            file.flush()
        try:
            _lock(file)
        except OSError as error:
            raise RuntimeError("Another batch owns this output folder. Monitor it instead.") from error
        try:
            yield
        finally:
            _unlock(file)

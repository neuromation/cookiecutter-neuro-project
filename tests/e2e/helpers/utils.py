import os
import shutil
import signal
import time
import typing as t
from contextlib import contextmanager
from pathlib import Path

from tests.e2e.configuration import unique_label
from tests.e2e.helpers.logs import LOGGER, log_msg


# == local file helpers ==


def generate_random_file(path: Path, size_b: int) -> Path:
    name = f"{unique_label()}.tmp"
    path_and_name = path / name
    with path_and_name.open("wb") as file:
        generated = 0
        while generated < size_b:
            length = min(1024 * 1024, size_b - generated)
            data = os.urandom(length)
            file.write(data)
            generated += len(data)
    return path_and_name


def cleanup_local_dirs(*dirs: t.Union[str, Path]) -> None:
    for d_or_name in dirs:
        if isinstance(d_or_name, str):
            d = Path(d_or_name)
        else:
            d = d_or_name
        log_msg(f"Cleaning up local directory `{d.absolute()}`")
        assert d.is_dir(), f"not a dir: {d}"
        assert d.exists(), f"not exists before cleanup: {d}"
        for f in d.iterdir():
            if f.is_file():
                f.unlink()
        assert d.exists(), f"not exists after cleanup: {d}"
        assert not list(d.iterdir()), "directory should be empty here"


def copy_local_files(from_dir: Path, to_dir: Path, glob: str = "*") -> None:
    for f in from_dir.glob(glob):
        if not f.is_file():
            continue
        target = to_dir / f.name
        if target.exists():
            log_msg(f"Target `{target.absolute()}` already exists")
            continue
        log_msg(f"Copying file `{f}` to `{target.absolute()}`")
        shutil.copyfile(str(f), target, follow_symlinks=False)


# == helpers ==
@contextmanager
def timeout(time_s: int) -> t.Iterator[None]:
    """ source: https://www.jujens.eu/posts/en/2018/Jun/02/python-timeout-function/
    """

    def raise_timeout(signum: int, frame: t.Any) -> t.NoReturn:
        raise TimeoutError

    # Register a function to raise a TimeoutError on the signal.
    signal.signal(signal.SIGALRM, raise_timeout)
    # Schedule the signal to be sent after ``time``.
    signal.alarm(time_s)

    try:
        yield
    except TimeoutError:
        log_msg(f"TIMEOUT ERROR: {time_s} sec", logger=LOGGER.error)
        raise
    finally:
        # Unregister the signal so it won't be triggered
        # if the timeout is not reached.
        signal.signal(signal.SIGALRM, signal.SIG_IGN)


@contextmanager
def measure_time(command_name: str = "") -> t.Iterator[None]:
    log_msg("=" * 100)
    start_time = time.time()
    log_msg(f"Measuring time for command: `{command_name}`")
    yield
    elapsed_time = time.time() - start_time
    log_msg("=" * 50)
    log_msg(f"  TIME SUMMARY [{command_name}]: {elapsed_time:.2f} sec")
    log_msg("=" * 50)


@contextmanager
def log_errors_and_finalize(
    finalizer_callback: t.Optional[t.Callable[[], t.Any]] = None
) -> t.Iterator[None]:
    try:
        yield
    except Exception as e:
        log_msg("-" * 100, logger=LOGGER.error)
        log_msg(f"Error: {e.__class__}: {e}", logger=LOGGER.error)
        log_msg("-" * 100, logger=LOGGER.error)
        raise
    finally:
        if finalizer_callback is not None:
            log_msg("Running finalization callback...")
            finalizer_callback()
            log_msg("Done")

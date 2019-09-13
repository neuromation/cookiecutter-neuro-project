import logging
import os
import re
import shutil
import signal
import sys
import textwrap
import time
import typing as t
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

import pexpect
import pytest

from tests.e2e.configuration import (
    MK_CODE_PATH,
    MK_DATA_PATH,
    MK_NOTEBOOKS_PATH,
    MK_PROJECT_NAME,
    PACKAGES_APT_CUSTOM,
    PACKAGES_PIP_CUSTOM,
    PROJECT_APT_FILE_NAME,
    PROJECT_PIP_FILE_NAME,
    TIMEOUT_NEURO_LOGIN,
)
from tests.utils import inside_dir


CHILD_PROCESSES_OUTPUT_LOGFILE = sys.stdout  # stdout or file


LOGGER_NAME = "e2e"

SUBMITTED_JOBS_FILE_NAME = "submitted_jobs.txt"
CLEANUP_JOBS_SCRIPT_NAME = "cleanup_jobs.py"


DEFAULT_TIMEOUT_SHORT = 10
DEFAULT_TIMEOUT_LONG = 10 * 60

# TODO: use a real dataset after cleaning up docs
FILE_SIZE_KB = 4
FILE_SIZE_B = FILE_SIZE_KB * 1024
N_FILES = 100


VERBS_SECRET = ("login-with-token",)
VERBS_JOB_RUN = ("run", "submit")

# OutCode = namedtuple("OutCode", "output code")
ESCAPE_LOG_CHARACTERS: t.Sequence[t.Tuple[str, str]] = [("\n", "\\n")]

# all variables prefixed "LOCAL_" store paths to file on your local machine
LOCAL_ROOT_PATH = Path(__file__).resolve().parent.parent.parent
LOCAL_TESTS_ROOT_PATH = LOCAL_ROOT_PATH / "tests"
LOCAL_TESTS_SAMPLES_PATH = LOCAL_TESTS_ROOT_PATH / "samples"
LOCAL_SUBMITTED_JOBS_FILE = LOCAL_ROOT_PATH / SUBMITTED_JOBS_FILE_NAME
LOCAL_SUBMITTED_JOBS_CLEANER_SCRIPT_PATH = LOCAL_ROOT_PATH / CLEANUP_JOBS_SCRIPT_NAME
LOCAL_PROJECT_CONFIG_PATH = LOCAL_TESTS_ROOT_PATH / "cookiecutter.yaml"


# note: ERROR, being the most general error, must go the last
DEFAULT_NEURO_ERROR_PATTERNS = ("404: Not Found", "Status: failed", "ERROR")
DEFAULT_MAKE_ERROR_PATTERNS = ("Makefile:", "make: ", "recipe for target ")
DEFAULT_ERROR_PATTERNS = DEFAULT_MAKE_ERROR_PATTERNS + DEFAULT_NEURO_ERROR_PATTERNS


PEXPECT_BUFFER_SIZE_BYTES = 50 * 1024


def get_logger() -> logging.Logger:
    logger = logging.getLogger(LOGGER_NAME)
    return logger


log = get_logger()


def pytest_logger_config(logger_config: t.Any) -> None:
    """Pytest logging setup"""
    loggers = [LOGGER_NAME]
    logger_config.add_loggers(loggers, stdout_level="info")
    logger_config.set_log_option_default(",".join(loggers))


JOB_ID_PATTERN = re.compile(
    # pattern for UUID v4 taken here: https://stackoverflow.com/a/38191078
    r"(job-[0-9a-f]{8}-[0-9a-f]{4}-[4][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12})",
    re.IGNORECASE,
)


# == fixtures ==


@pytest.fixture(scope="session", autouse=True)
def change_directory_to_temp(tmpdir_factory: t.Any) -> t.Iterator[None]:
    tmp = tmpdir_factory.mktemp("test-cookiecutter")
    with inside_dir(str(tmp)):
        yield


@pytest.fixture(scope="session", autouse=True)
def run_cookiecutter(change_directory_to_temp: None) -> t.Iterator[None]:
    run_command(
        f"cookiecutter --no-input "
        f"--config-file={LOCAL_PROJECT_CONFIG_PATH} {LOCAL_ROOT_PATH}"
    )
    with inside_dir(MK_PROJECT_NAME):
        yield


@pytest.fixture(scope="session", autouse=True)
def generate_empty_project(run_cookiecutter: None) -> None:
    log.info(f"Initializing empty project: `{Path().absolute()}`")

    apt_file = Path(PROJECT_APT_FILE_NAME)
    log.info(f"Copying `{apt_file}`")
    assert apt_file.is_file() and apt_file.exists()
    with apt_file.open("a") as f:
        for package in PACKAGES_APT_CUSTOM:
            f.write("\n" + package)

    pip_file = Path(PROJECT_PIP_FILE_NAME)
    log.info(f"Copying `{pip_file}`")
    assert pip_file.is_file() and pip_file.exists()
    with pip_file.open("a") as f:
        for package in PACKAGES_PIP_CUSTOM:
            f.write("\n" + package)

    data_dir = Path(MK_DATA_PATH)
    log.info(f"Generating data to `{data_dir}/`")
    assert data_dir.is_dir() and data_dir.exists()
    for _ in range(N_FILES):
        generate_random_file(data_dir, FILE_SIZE_B)
    assert len(list(data_dir.iterdir())) >= N_FILES

    code_dir = Path(MK_CODE_PATH)
    log.info(f"Generating code files to `{code_dir}/`")
    assert code_dir.is_dir() and code_dir.exists()
    code_file = code_dir / "main.py"
    with code_file.open("w") as f:
        f.write(
            textwrap.dedent(
                """\
        if __name__ == "__main__":
            print("test script")
        """
            )
        )
    assert code_file.exists()

    notebooks_dir = Path(MK_NOTEBOOKS_PATH)
    assert notebooks_dir.is_dir() and notebooks_dir.exists()
    copy_local_files(LOCAL_TESTS_SAMPLES_PATH, notebooks_dir)
    assert list(notebooks_dir.iterdir())


@pytest.fixture(scope="session", autouse=True)
def pip_install_neuromation() -> None:
    output = run_command("pip install -U neuromation")
    # stderr can contain: "You are using pip version..."
    patterns = (
        "Requirement already up-to-date:.* neuromation",
        "Installing collected packages:.* neuromation"
        "Successfully installed.* neuromation",
    )
    assert any(re.search(p, output) for p in patterns), f"output: `{output}`"
    assert "Name: neuromation" in run_command("pip show neuromation")


@pytest.fixture(scope="session", autouse=True)
def neuro_login(pip_install_neuromation: None) -> t.Iterator[None]:
    token = os.environ["COOKIECUTTER_TEST_E2E_TOKEN"]
    url = os.environ["COOKIECUTTER_TEST_E2E_URL"]
    try:
        captured = run_command(
            f"neuro config login-with-token {token} {url}",
            timeout=TIMEOUT_NEURO_LOGIN,
            debug=False,
        )
        assert f"Logged into {url}" in captured, f"stdout: `{captured}`"
        log.info(run_command("neuro config show"))
        yield
    finally:
        run_command(
            f"python '{LOCAL_SUBMITTED_JOBS_CLEANER_SCRIPT_PATH.absolute()}'",
            debug=True,
        )
        if os.environ.get("CI") == "true":
            nmrc = Path("~/.nmrc").expanduser()
            log.info(f"Deleting {nmrc} file")
            nmrc.unlink()
            log.info("Deleted")


# == helpers ==


def unique_label() -> str:
    return uuid4().hex[:8]


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
        log.error(f"TIMEOUT ERROR: {time_s}")
        raise
    finally:
        # Unregister the signal so it won't be triggered
        # if the timeout is not reached.
        signal.signal(signal.SIGALRM, signal.SIG_IGN)


@contextmanager
def measure_time(command_name: str = "") -> t.Iterator[None]:
    log.info("-" * 50)
    log.info(f'TESTING COMMAND: "{command_name}"')
    start_time = time.time()
    yield
    elapsed_time = time.time() - start_time
    log.info("=" * 50)
    log.info(f"  TIME SUMMARY [{command_name}]: {elapsed_time:.2f} sec")
    log.info("=" * 50)


def run_command(
    cmd: str,
    *,
    debug: bool = False,
    detect_new_jobs: bool = True,
    timeout: int = DEFAULT_TIMEOUT_LONG,
    expect_patterns: t.Sequence[str] = (),
    stop_patterns: t.Sequence[str] = (),  # ignore errors (and stderr) by default
) -> str:
    """
    >>> # Check expected-outputs:
    >>> s = run_command("bash -c 'echo 1; echo 2; echo 3'",
    ...          debug=False,
    ...          expect_patterns=['1', '2'])
    >>> s.split()
    ['1', '2', '3']
    >>> # Check expected-outputs:
    >>> try:
    ...     run_command("bash -c 'echo 1; echo 2; echo 3'",
    ...          debug=False,
    ...          expect_patterns=['1', '3'],
    ...          stop_patterns=['2'])
    ... except RuntimeError as e:
    ...     assert str(e) == "Found stop-pattern: re.compile('2', re.DOTALL)"
    >>> # Works with only stop-patterns:
    >>> try:
    ...     run_command("bash -c 'echo 1; echo 2; echo 3'",
    ...          debug=False,
    ...          stop_patterns=['2'])
    ... except RuntimeError as e:
    ...     assert str(e) == "Found stop-pattern: re.compile('2', re.DOTALL)"
    >>> # Pattern not found at all:
    >>> try:
    ...     run_command("bash -c 'echo 1; echo 2; echo 3'",
    ...          debug=False,
    ...          expect_patterns=['1', '2', '3', '4'])
    ... except RuntimeError as e:
    ...     assert str(e) == "Could not find pattern: '4'"
    """

    child = pexpect.spawn(
        cmd,
        timeout=timeout,
        logfile=CHILD_PROCESSES_OUTPUT_LOGFILE if debug else None,
        maxread=PEXPECT_BUFFER_SIZE_BYTES,
        searchwindowsize=PEXPECT_BUFFER_SIZE_BYTES // 100,
        encoding="utf-8",
    )

    compile_flags = re.DOTALL
    if child.ignorecase:
        compile_flags = compile_flags | re.IGNORECASE
    stop_patterns_compiled = [re.compile(p, compile_flags) for p in stop_patterns]
    if stop_patterns:
        log.info(f"Stop-patterns: {repr(stop_patterns)}")

    output = ""
    try:
        for expected in expect_patterns:
            log.info(f"Searching pattern: {repr(expected)}")
            expected_p = re.compile(expected, compile_flags)
            try:
                child.expect_list([expected_p] + stop_patterns_compiled)
                chunk = _get_chunk(child)
                output += chunk
            except pexpect.EOF:
                raise RuntimeError(f"Could not find pattern: {repr(expected)}")

            _check_chunk_not_contains_stop_patterns(chunk, stop_patterns_compiled)

        # read the rest:
        child.wait()
        # TODO: read huge chunk in chunks
        chunk = child.read()
        if chunk:
            output += chunk
            _check_chunk_not_contains_stop_patterns(chunk, stop_patterns_compiled)

        return output

    except RuntimeError as e:
        log.error(str(e))
        log.error(f"Dump: `{repr(output)}`")
        raise

    finally:
        if detect_new_jobs:
            _dump_submitted_job_ids(_detect_job_ids(output))


def _get_chunk(child: pexpect.pty_spawn.spawn) -> str:
    chunk = child.before
    if isinstance(child.after, child.allowed_string_types):
        chunk += child.after
    return chunk


def _check_chunk_not_contains_stop_patterns(
    chunk: str, stop_patterns_compiled: t.List[t.Pattern[str]]
) -> None:
    for stop_p in stop_patterns_compiled:
        if stop_p.search(chunk):
            raise RuntimeError(f"Found stop-pattern: {repr(stop_p)}")


def _detect_job_ids(stdout: str) -> t.Set[str]:
    return set(JOB_ID_PATTERN.findall(stdout))


def _dump_submitted_job_ids(jobs: t.Iterable[str]) -> None:
    if jobs:
        log.info(f"Dumped jobs: {jobs}")
        with LOCAL_SUBMITTED_JOBS_FILE.open("a") as f:
            f.write("\n" + "\n".join(jobs))


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
        log.info(f"Cleaning up local directory `{d.absolute()}`")
        for f in d.iterdir():
            if f.is_file():
                f.unlink()
        assert not list(d.iterdir()), "directory should be empty here"


def copy_local_files(from_dir: Path, to_dir: Path) -> None:
    for f in from_dir.glob("*"):
        if not f.is_file():
            continue
        target = to_dir / f.name
        if target.exists():
            log.info(f"Target `{target.absolute()}` already exists")
            continue
        log.info(f"Copying file `{f}` to `{target.absolute()}`")
        shutil.copyfile(f, target, follow_symlinks=False)


# == neuro helpers ==


def neuro_ls(path: str, timeout: int, ignore_errors: bool = False) -> t.Set[str]:
    out = run_command(
        f"neuro ls {path}",
        timeout=timeout,
        debug=True,
        stop_patterns=[] if ignore_errors else list(DEFAULT_NEURO_ERROR_PATTERNS),
    )
    result = set(out.split())
    if ".gitkeep" in result:
        result.remove(".gitkeep")
    return result


def neuro_rm_dir(
    project_relative_path: str, timeout: int, ignore_errors: bool = False
) -> None:
    log.info(f"Deleting remote directory `{project_relative_path}`")
    run_command(
        f"neuro rm -r {project_relative_path}",
        timeout=timeout,
        debug=False,
        stop_patterns=[] if ignore_errors else list(DEFAULT_NEURO_ERROR_PATTERNS),
    )
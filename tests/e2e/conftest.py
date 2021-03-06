import logging
import pytest
import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Iterator

from tests.utils import inside_dir


PROJECT_NAME = "My e2e project"
MK_PROJECT = PROJECT_NAME.lower().replace(" ", "-")
PATH_ROOT = Path(__file__).resolve().parent.parent.parent


@pytest.fixture(scope="session", autouse=True)
def change_directory_to_temp() -> Iterator[None]:
    tmp = Path(tempfile.mkdtemp(prefix="test-cookiecutter-"))
    for path in PATH_ROOT.iterdir():
        if path.is_file():
            shutil.copy(path, tmp / path.name)
        else:
            shutil.copytree(path, tmp / path.name)

    with inside_dir(tmp):
        yield


@pytest.fixture(scope="session", autouse=True)
def cookiecutter_setup(change_directory_to_temp: None) -> Iterator[None]:
    exec(f"cookiecutter --no-input . project_name='{PROJECT_NAME}'")
    with inside_dir(MK_PROJECT):
        logging.info(f"Working inside test project: {Path().absolute()}")
        yield


def exec(cmd: str, assert_exit_code: bool = True) -> "subprocess.CompletedProcess[str]":
    proc = subprocess.run(
        shlex.split(cmd),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
    )
    if assert_exit_code and proc.returncode != 0:
        raise RuntimeError(f"Non-zero exit code {proc.returncode} for `{cmd}`: {proc}")
    return proc

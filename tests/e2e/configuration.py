TIMEOUT_MAKE_SETUP = 6 * 60
TIMEOUT_MAKE_UPLOAD_CODE = 5
TIMEOUT_MAKE_CLEAN_CODE = 3
TIMEOUT_MAKE_UPLOAD_DATA = 500
TIMEOUT_MAKE_CLEAN_DATA = 50
TIMEOUT_MAKE_UPLOAD_NOTEBOOKS = TIMEOUT_MAKE_DOWNLOAD_NOTEBOOKS = 5
TIMEOUT_MAKE_CLEAN_NOTEBOOKS = 5
# TIMEOUT_MAKE_DOWNLOAD

TIMEOUT_NEURO_LOGIN = 5
TIMEOUT_NEURO_RUN = 30
TIMEOUT_NEURO_LS = 4
TIMEOUT_NEURO_PS = 4


# all variables prefixed "MK_" are taken from Makefile (without prefix)
# Project name is defined in cookiecutter.yaml, from `project_name`
MK_PROJECT_NAME = "test-project"

MK_CODE_PATH = "modules"
MK_DATA_PATH = "data"
MK_NOTEBOOKS_PATH = "notebooks"
MK_REQUIREMENTS_PATH = "requirements"
MK_RESULTS_PATH = "results"
MK_PROJECT_PATH_STORAGE = f"storage:{MK_PROJECT_NAME}"
MK_CODE_PATH_STORAGE = f"{MK_PROJECT_PATH_STORAGE}/{MK_CODE_PATH}"
MK_DATA_PATH_STORAGE = f"{MK_PROJECT_PATH_STORAGE}/{MK_DATA_PATH}"
MK_NOTEBOOKS_PATH_STORAGE = f"{MK_PROJECT_PATH_STORAGE}/{MK_NOTEBOOKS_PATH}"
MK_REQUIREMENTS_PATH_STORAGE = f"{MK_PROJECT_PATH_STORAGE}/{MK_REQUIREMENTS_PATH}"
MK_RESULTS_PATH_STORAGE = f"{MK_PROJECT_PATH_STORAGE}/{MK_RESULTS_PATH}"

MK_PROJECT_PATH_ENV = "/project"
MK_CODE_PATH_ENV = f"{MK_PROJECT_PATH_ENV}/{MK_CODE_PATH}"
MK_DATA_PATH_ENV = f"{MK_PROJECT_PATH_ENV}/{MK_DATA_PATH}"
MK_NOTEBOOKS_PATH_ENV = f"{MK_PROJECT_PATH_ENV}/{MK_NOTEBOOKS_PATH}"
MK_REQUIREMENTS_PATH_ENV = f"{MK_PROJECT_PATH_ENV}/{MK_REQUIREMENTS_PATH}"
MK_RESULTS_PATH_ENV = f"{MK_PROJECT_PATH_ENV}/{MK_RESULTS_PATH}"

MK_SETUP_NAME = "setup"
MK_TRAINING_NAME = "training"
MK_JUPYTER_NAME = "jupyter"
MK_TENSORBOARD_NAME = "tensorboard"
MK_FILEBROWSER_NAME = "filebrowser"

MK_BASE_ENV_NAME = "image:neuro/base"
MK_CUSTOM_ENV_NAME = "image:neuro/custom"


PROJECT_APT_FILE_NAME = "apt.txt"
PROJECT_PIP_FILE_NAME = "requirements.txt"

# note: apt package 'expect' requires user input during installation
PACKAGES_APT_CUSTOM = ["python", "expect", "figlet"]
PACKAGES_PIP_CUSTOM = ["aiohttp==3.5.4", "aiohttp_security==0.4.0", "neuromation"]

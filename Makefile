LINTER_DIRS := tests
NEURO_COMMAND := "neuro --verbose --show-traceback"

.PHONY: init
init:
	pip install -r requirements-dev.txt

.PHONY: cook
cook:
	cookiecutter gh:neuromation/cookiecutter-neuro-project

.PHONY: lint
lint:
	isort -c -rc ${LINTER_DIRS}
	black --check $(LINTER_DIRS)
	mypy $(LINTER_DIRS)
	flake8 $(LINTER_DIRS)

.PHONY: format
format:
	isort -rc $(LINTER_DIRS)
	black $(LINTER_DIRS)

.PHONY: test_unit
test_unit:
	pytest -v -s tests/unit
	cookiecutter --no-input --config-file ./tests/cookiecutter.yaml --output-dir .. .
	stat ../test_project
	python -m doctest tests/e2e/conftest.py

.PHONY: test_e2e_dev
test_e2e_dev:
	TRAINING_MACHINE_TYPE=cpu-small NEURO=$(NEURO_COMMAND)  pytest -s -v --environment=dev --tb=short tests/e2e

.PHONY: test_e2e_staging
test_e2e_staging:
	TRAINING_MACHINE_TYPE=gpu-small NEURO=$(NEURO_COMMAND)  pytest -s -v --environment=staging --tb=short tests/e2e

.PHONY: cleanup_e2e
cleanup_e2e:
	bash -c tests/e2e/cleanup.sh

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
	stat ../test-project
	python -m doctest tests/e2e/conftest.py

.PHONY: test_e2e_dev
test_e2e_dev:
	PRESET=cpu-small NEURO=$(NEURO_COMMAND)  pytest -s -v --environment=dev --tb=short tests/e2e -k test_nothing

.PHONY: test_e2e_staging
test_e2e_staging:
	PRESET=gpu-small NEURO=$(NEURO_COMMAND)  pytest -s -v --environment=staging --tb=short tests/e2e

.PHONY: get_e2e_failures
get_e2e_failures:
	@[ -f tests/e2e/output/failures.txt ] && cat tests/e2e/output/failures.txt || echo "(no data)"

.PHONY: cleanup_e2e
cleanup_e2e:
	bash -c tests/e2e/cleanup.sh

VENV_NAME := .venv
INSTALL_SCRIPT := ./scripts/init_venv.sh
.DEFAULT_GOAL := help
.PHONY: venv clean install run_dt run_random_metric_gen update_core_schema

define PRINT_HELP_PYSCRIPT
import re, sys

for line in sys.stdin:
	match = re.match(r'^([a-zA-Z_-]+):.*?## (.*)$$', line)
	if match:
		target, help = match.groups()
		print("%-20s %s" % (target, help))
endef
export PRINT_HELP_PYSCRIPT

help: ## displays help
	@python3 -c "$$PRINT_HELP_PYSCRIPT" < $(MAKEFILE_LIST)

venv: ## creates .venv if it does not exist
	@test -d $(VENV_NAME) || ./$(INSTALL_SCRIPT)

build: venv ## builds the project
	. $(VENV_NAME)/bin/activate && poetry build

clean: ## removes venv and dist
	@echo "Cleaning up..."
	rm -rf $(VENV_NAME)
	rm -rf ./dist
	(docker stop influxdb || true) && (docker rm influxdb || true)
	rm -rf ./influxdb_data

install: venv  ## installs the project with poetry
	. $(VENV_NAME)/bin/activate && poetry install --extras dev

run_dt: venv ## runs digital twin api
	. $(VENV_NAME)/bin/activate &&  python src/digital_twin/main.py

run_influxdb: ## runs a local influxdb with docker and sets .env
	./scripts/run_influxdb.sh

update_core_schema: venv ## update core pydantic model based on configs/DT_json_schema.json
	. $(VENV_NAME)/bin/activate && ./scripts/generate_model.sh

lint: venv ## show linting errors
	@. $(VENV_NAME)/bin/activate && ruff check

format: venv ## formats the code
	@. $(VENV_NAME)/bin/activate && ruff format

emulate: venv ## run ./script/emulate.sh with defaults
	@. $(VENV_NAME)/bin/activate && ./scripts/emulate.sh

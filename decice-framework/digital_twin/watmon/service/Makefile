VENV_NAME := .venv
INSTALL_SCRIPT := ./scripts/init_venv.sh
.DEFAULT_GOAL := help
.PHONY: venv clean install
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

install: venv  ## installs the project with poetry
	. $(VENV_NAME)/bin/activate && poetry install --with dev

lint: venv ## show linting errors 
	@. $(VENV_NAME)/bin/activate && ruff check

format: venv ## formats the code
	@. $(VENV_NAME)/bin/activate && ruff format

run_api: venv ## runs the rest api
	@. $(VENV_NAME)/bin/activate && python watmon_service/api.py

container_build: ## builds the Docker container
	docker build -t watmon_decice_service -f deployment/Dockerfile .

container_save: container_build ## saves the built image into file
	docker save watmon_decice_service > ./deployment/dist/watmon_decice_service.tar
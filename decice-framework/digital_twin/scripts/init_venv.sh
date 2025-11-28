#!/usr/bin/env bash

# Check for python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')

MIN_VERSION="3.10"

# if [ "${MIN_VERSION}" != "${PYTHON_VERSION}" ] && \
#     [ "${PYTHON_VERSION}" = "`echo -e "${PYTHON_VERSION}\n${MIN_VERSION}" | sort -V | head -n1`" ]; then
#   echo "Python 3.10 or higher is not installed."
#   exit 0
# fi

# Set virtual environment directory
if [ $# -eq 0 ]; then
  VENV_DIR=".venv"
else
  VENV_DIR="$1"
fi

#configure venv
python3.12 -m venv "$VENV_DIR"

source "$VENV_DIR"/bin/activate

python -m pip install --upgrade pip

pip install poetry

poetry config virtualenvs.in-project true

echo ""
echo "Created ${VENV_DIR} and installed poetry"
echo ""

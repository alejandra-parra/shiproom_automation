#!/bin/bash
# Wrapper script to run the Jellyfish API test script with proper PYTHONPATH

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="${SCRIPT_DIR}/package:${PYTHONPATH}"

python3 "${SCRIPT_DIR}/test_jellyfish_api.py" "$@"
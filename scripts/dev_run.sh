#!/usr/bin/env bash
set -euo pipefail
export POLICY_PATH=${POLICY_PATH:-$(pwd)/config/policy.yaml}
export DATA_DIR=${DATA_DIR:-$(pwd)/data}
uvicorn app.api:app --reload --port 8080

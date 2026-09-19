#!/usr/bin/env bash
# 로컬 jeff 서버에 붙여서 예제 실행:  ./run_local.sh 01_basics.py
set -euo pipefail
export TYPESAFE_API_KEY=devkey
export TYPESAFE_BASE_URL=http://localhost:8000
exec "$(dirname "$0")/.venv/bin/python" "$@"

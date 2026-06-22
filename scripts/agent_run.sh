#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || {
  echo "오류: NewsLab Git repository에서 실행하세요." >&2
  exit 2
}

cd "$REPO_ROOT"
exec python -m scripts.agent_workflow.cli "$@"

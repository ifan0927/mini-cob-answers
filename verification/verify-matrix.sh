#!/usr/bin/env bash
# Re-runs the full verification matrix. Extra arguments go to verify_matrix.py, e.g.
#   ./verify-matrix.sh --learner ../../mini-cob-learner
#   ./verify-matrix.sh --only 04,10 --repeat 5
set -euo pipefail
cd "$(dirname "$0")"
exec python3 verify_matrix.py "$@"

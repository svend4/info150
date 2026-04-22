#!/usr/bin/env bash
# Run mutmut against the triage-critical modules.
#
# Prereqs:   pip install -e '.[dev,mutation]'
# Usage:     ./scripts/run_mutation.sh                # full run
#            ./scripts/run_mutation.sh --quick        # first failing file only
#            ./scripts/run_mutation.sh results        # show summary after run
#
# Output lives in .mutmut-cache (add to .gitignore).
# A full run on the default module set takes ~5–15 min on a laptop.

set -euo pipefail

cd "$(dirname "$0")/.."

if ! command -v mutmut >/dev/null 2>&1; then
    echo "error: mutmut not installed. Run: pip install -e '.[dev,mutation]'" >&2
    exit 2
fi

case "${1:-run}" in
    run)
        mutmut run
        echo
        echo "Run complete. Summary:"
        mutmut results
        ;;
    --quick)
        mutmut run --paths-to-mutate triage4/triage_reasoning/score_fusion.py
        mutmut results
        ;;
    results)
        mutmut results
        ;;
    show)
        # Show the diff for a specific mutant id (passed as $2).
        mutmut show "${2:?missing mutant id}"
        ;;
    *)
        echo "usage: $0 [run|--quick|results|show <id>]" >&2
        exit 2
        ;;
esac

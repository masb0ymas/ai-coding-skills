#!/usr/bin/env bash
# Run every maintenance check on a gofi project and print a summary.
#
#   bash health.sh [project-dir] [--quick]
#
# --quick skips govulncheck and the race-enabled test run.
# Set TEST_DB_DSN to a disposable PostgreSQL 18 database to include the
# cmd/api integration test (it wipes that database).
set -uo pipefail

ROOT="."
QUICK=0
for arg in "$@"; do
  case "$arg" in
    --quick) QUICK=1 ;;
    *) ROOT="$arg" ;;
  esac
done
cd "$ROOT" || { echo "cannot cd to $ROOT"; exit 2; }
[ -f go.mod ] || { echo "no go.mod in $(pwd)"; exit 2; }

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AUDIT="$SKILL_DIR/../layers/scripts/audit_layers.py"

declare -a RESULTS
FAILED=0

step() {
  local name="$1"; shift
  printf '\n==> %s\n' "$name"
  if "$@"; then
    RESULTS+=("PASS  $name")
  else
    RESULTS+=("FAIL  $name")
    FAILED=1
  fi
}

gofmt_clean() {
  local out
  out=$(find . -name '*.go' -not -path './vendor/*' -not -path '*/.*' -print0 | xargs -0 -r gofmt -l)
  [ -z "$out" ] || { echo "not gofmt'ed:"; echo "$out"; return 1; }
}

step "gofmt"             gofmt_clean
step "go mod verify"     go mod verify
step "go mod tidy"       go mod tidy -diff
step "go build"          go build ./...
step "go vet"            go vet ./...
if [ "$QUICK" = 1 ]; then
  step "go test"         go test ./...
else
  step "go test -race"   go test -race -count=1 ./...
  step "govulncheck"     go run golang.org/x/vuln/cmd/govulncheck@v1.8.0 ./...
fi
step "env sync"          python3 "$SKILL_DIR/scripts/check_env_sync.py" --root .
if [ -f "$AUDIT" ]; then
  step "layer audit"     python3 "$AUDIT" --root .
else
  RESULTS+=("SKIP  layer audit (layers skill not found next to this one)")
fi
[ -n "${TEST_DB_DSN:-}" ] || RESULTS+=("NOTE  TEST_DB_DSN unset: cmd/api integration test was skipped")

printf '\n==> summary\n'
printf '%s\n' "${RESULTS[@]}"
echo
echo "ponytail markers (deliberate limits to revisit when scaling out):"
grep -rn --include='*.go' 'ponytail:' . | sed 's/^/  /' || true
exit $FAILED

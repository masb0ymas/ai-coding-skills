#!/usr/bin/env bash
# Run every maintenance check on a vine app and print a summary.
#
#   bash health.sh [app-dir] [--quick]
#
# --quick skips the production build and pnpm audit.
set -uo pipefail

ROOT="."
QUICK=0
for arg in "$@"; do
  case "$arg" in
    --quick) QUICK=1 ;;
    *) ROOT="$arg" ;;
  esac
done
# Resolved before the cd below, so a relative script path still works.
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AUDIT="$SKILL_DIR/../layers/scripts/audit_layers.py"

cd "$ROOT" || { echo "cannot cd to $ROOT"; exit 2; }
[ -f package.json ] || { echo "no package.json in $(pwd)"; exit 2; }

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

# The vite route tree is generated but committed; a build that rewrites it
# means someone added a route without regenerating.
route_tree_fresh() {
  local tree=src/routeTree.gen.ts before
  [ -f "$tree" ] || return 0
  before=$(cksum < "$tree")
  pnpm exec tsr generate >/dev/null 2>&1 || { echo "tsr generate failed"; return 1; }
  [ "$before" = "$(cksum < "$tree")" ] || { echo "$tree was stale (regenerated; review and commit)"; return 1; }
}

step "pnpm install --frozen-lockfile" pnpm install --frozen-lockfile
step "typecheck"                      pnpm exec tsc --noEmit -p .
step "route tree"                     route_tree_fresh
step "env sync"                       python3 "$SKILL_DIR/scripts/check_env_sync.py" --root .
if [ -f "$AUDIT" ]; then
  step "layer audit"                  python3 "$AUDIT" --root .
else
  RESULTS+=("SKIP  layer audit (layers skill not found next to this one)")
fi
if [ "$QUICK" = 0 ]; then
  step "build"                        pnpm build
  step "pnpm audit (prod, high)"      pnpm audit --prod --audit-level high
fi

printf '\n==> outdated (informational)\n'
pnpm outdated --format list 2>/dev/null | head -40 || true

printf '\n==> summary\n'
printf '%s\n' "${RESULTS[@]}"
echo
echo "ponytail markers (deliberate limits to revisit):"
grep -rn --include='*.ts' --include='*.tsx' --exclude-dir=node_modules 'ponytail:' . | sed 's/^/  /' || true
exit $FAILED

#!/usr/bin/env bash
# Run every maintenance check on a WXT extension and print a summary.
#
#   bash health.sh [project-dir] [--quick]
#
# --quick skips the production builds and the dependency audit.
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
AUDIT="$SKILL_DIR/../entrypoints/scripts/audit_entrypoints.py"

cd "$ROOT" || { echo "cannot cd to $ROOT"; exit 2; }
[ -f package.json ] || { echo "no package.json in $(pwd)"; exit 2; }

if   [ -f pnpm-lock.yaml ]; then PM=pnpm; INSTALL=(pnpm install --frozen-lockfile); X=(pnpm exec); AUDIT_CMD=(pnpm audit --prod --audit-level high)
elif [ -f bun.lock ] || [ -f bun.lockb ]; then PM=bun; INSTALL=(bun install --frozen-lockfile); X=(bunx); AUDIT_CMD=(bun audit --audit-level=high)
elif [ -f yarn.lock ]; then
  PM=yarn; X=(yarn)
  # Yarn 1 silently ignores --immutable, Berry dropped --frozen-lockfile.
  if [ "$(yarn --version | cut -d. -f1)" = 1 ]; then
    INSTALL=(yarn install --frozen-lockfile); AUDIT_CMD=(yarn audit --groups dependencies --level high)
  else
    INSTALL=(yarn install --immutable); AUDIT_CMD=(yarn npm audit --environment production --severity high)
  fi
else PM=npm; INSTALL=(npm ci); X=(npx --no-install); AUDIT_CMD=(npm audit --omit=dev --audit-level=high)
fi

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

step "$PM install (frozen lockfile)" "${INSTALL[@]}"
step "wxt prepare"                    "${X[@]}" wxt prepare
step "typecheck"                      "${X[@]}" tsc --noEmit
if [ -f "$AUDIT" ]; then
  step "entrypoint audit"             python3 "$AUDIT" --root .
else
  RESULTS+=("SKIP  entrypoint audit (entrypoints skill not found next to this one)")
fi
if grep -q '"vitest"' package.json; then
  step "unit tests"                   "${X[@]}" vitest run
fi
if [ "$QUICK" = 0 ]; then
  step "build chrome"                 "${X[@]}" wxt build
  step "build firefox"                "${X[@]}" wxt build -b firefox
  step "$PM audit (prod, high)"       "${AUDIT_CMD[@]}"
fi

printf '\n==> outdated (informational)\n'
$PM outdated 2>/dev/null | head -40 || true

printf '\n==> summary\n'
printf '%s\n' "${RESULTS[@]}"
echo
echo "ponytail markers (deliberate limits to revisit):"
grep -rn --include='*.ts' --include='*.tsx' --include='*.vue' --include='*.svelte' \
  --exclude-dir=node_modules --exclude-dir=.output --exclude-dir=.wxt 'ponytail:' . | sed 's/^/  /' || true
exit $FAILED

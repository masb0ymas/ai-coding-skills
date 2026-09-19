#!/bin/sh

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
SOURCE_ROOT=$SCRIPT_DIR
REPOSITORY_ARCHIVE=https://github.com/masb0ymas/ai-coding-skills/archive/refs/heads/main.tar.gz
TEMP_DIR=

cleanup() {
  if [ -n "$TEMP_DIR" ] && [ -d "$TEMP_DIR" ]; then
    rm -rf "$TEMP_DIR"
  fi
}

trap cleanup 0 HUP INT TERM

usage() {
  cat <<'EOF'
Usage: ./install.sh [--agent <agent>] [--skill <skill>] [--skip-graft-setup] [--graft-no-global] [destination]

Options:
  --agent <agent>      Agent target (default: all)
  --skill <skill>      Skill to install (default: all)
  --skip-graft-setup   Copy graft skill files only; skip CLI install, graft init, and verification
  --graft-no-global    Pass --no-global to graft init (repo-only wiring, no writes outside destination)
  -h, --help           Show this help

Agents:
  all          Install for every supported agent
  agents       Install to .agents/skills (Zed and Agent Skills clients)
  claude       Install to .claude/skills
  openclaude   Install to .openclaude/skills
  zcode        Install to .zcode/skills

Destination defaults to the current directory.

Graft skill setup:
  Installing --skill graft (or --skill all when graft exists) also runs:
    1. npm install -g @nanonets/graft (skipped if graft is already installed)
    2. graft init -y in the destination repository
    3. Verification that destination/graft/ exists, with a map-file count
  This step is skipped automatically for global installs into $HOME.
  Use --skip-graft-setup to copy skill files without running Graft.

Examples:
  ./install.sh
  ./install.sh --agent claude /path/to/project
  ./install.sh --skill authula /path/to/project
  ./install.sh --agent claude --skill authula "$HOME"
  ./install.sh --skill graft /path/to/project
  ./install.sh --skill graft --graft-no-global /path/to/project
  ./install.sh --skill graft --skip-graft-setup /path/to/project

Remote usage:
  curl -fsSL https://raw.githubusercontent.com/masb0ymas/ai-coding-skills/main/install.sh | sh
  curl -fsSL https://raw.githubusercontent.com/masb0ymas/ai-coding-skills/main/install.sh | sh -s -- --agent claude --skill authula /path/to/project
  curl -fsSL https://raw.githubusercontent.com/masb0ymas/ai-coding-skills/main/install.sh | sh -s -- --skill graft /path/to/project
EOF
}

fail() {
  printf '%s\n\n' "$1" >&2
  usage >&2
  exit 1
}

download_file() {
  url=$1
  output=$2

  if command -v curl >/dev/null 2>&1; then
    curl -fsSL "$url" -o "$output"
  elif command -v wget >/dev/null 2>&1; then
    wget -q "$url" -O "$output"
  else
    printf 'Remote installation requires curl or wget.\n' >&2
    exit 1
  fi
}

is_repository_root() {
  [ -f "$SOURCE_ROOT/install.sh" ] && [ -d "$SOURCE_ROOT/skills" ]
}

install_graft_cli() {
  if command -v graft >/dev/null 2>&1; then
    printf 'Graft CLI already installed: %s\n' "$(command -v graft)"
    return
  fi

  command -v npm >/dev/null 2>&1 || {
    printf 'Graft setup requires npm to install @nanonets/graft.\n' >&2
    exit 1
  }

  printf 'Installing Graft CLI...\n'
  npm install -g @nanonets/graft
}

count_graft_map_files() {
  graph_dir=$1
  map_files=$(find "$graph_dir" -type f \( -name '*.md' -o -name 'graph.json' -o -path "$graph_dir/.graph/*" \) -print 2>/dev/null)
  if [ -z "$map_files" ]; then
    printf '0'
    return
  fi
  printf '%s\n' "$map_files" | wc -l | tr -d ' '
}

setup_graft() {
  destination=$1
  graft_no_global=$2
  graph_dir="$destination/graft"

  printf '\nSetting up Graft in %s...\n' "$destination"
  install_graft_cli

  command -v graft >/dev/null 2>&1 || {
    printf 'Graft CLI installation did not provide a graft command.\n' >&2
    exit 1
  }

  init_args='init -y'
  if [ "$graft_no_global" = true ]; then
    init_args='init --no-global -y'
  fi

  printf 'Running graft %s in %s...\n' "$init_args" "$destination"
  # shellcheck disable=SC2086
  (CDPATH= cd -- "$destination" && graft $init_args)

  if [ ! -d "$graph_dir" ]; then
    printf 'Graft setup failed: %s was not created.\n' "$graph_dir" >&2
    exit 1
  fi

  map_count=$(count_graft_map_files "$graph_dir")
  printf 'Graft setup complete: %s exists with %s map file(s).\n' "$graph_dir" "$map_count"
}

prepare_source() {
  if is_repository_root && { [ -f "$0" ] || [ -n "$TEMP_DIR" ]; }; then
    return
  fi

  command -v tar >/dev/null 2>&1 || {
    printf 'Remote installation requires tar.\n' >&2
    exit 1
  }

  temp_base=${TMPDIR:-/tmp}
  TEMP_DIR=$(mktemp -d "$temp_base/ai-coding-skills.XXXXXX")
  archive="$TEMP_DIR/repository.tar.gz"

  printf 'Downloading AI Coding Skills...\n'
  download_file "$REPOSITORY_ARCHIVE" "$archive"
  tar -xzf "$archive" -C "$TEMP_DIR"
  SOURCE_ROOT="$TEMP_DIR/ai-coding-skills-main"

  if ! is_repository_root; then
    printf 'Downloaded repository does not contain the expected skills directory.\n' >&2
    exit 1
  fi
}

install_bundle() {
  bundle=$1
  destination=$2
  skill=$3

  prepare_source

  source_dir="$SOURCE_ROOT/skills"
  target_dir="$destination/$bundle/skills"

  if [ ! -d "$source_dir" ]; then
    printf 'Skills source not found: %s\n' "$source_dir" >&2
    exit 1
  fi

  mkdir -p "$target_dir"

  if [ "$skill" = all ]; then
    cp -R "$source_dir/." "$target_dir/"
    printf 'Installed all skills for %s -> %s\n' "$bundle" "$target_dir"
    return
  fi

  if [ ! -d "$source_dir/$skill" ]; then
    printf 'Skill not found: %s\n' "$skill" >&2
    exit 1
  fi

  cp -R "$source_dir/$skill" "$target_dir/"
  printf 'Installed %s for %s -> %s/%s\n' "$skill" "$bundle" "$target_dir" "$skill"
}

agent=all
skill=all
destination=.
destination_set=false
skip_graft_setup=false
graft_no_global=false

while [ "$#" -gt 0 ]; do
  case "$1" in
    --agent)
      [ "$#" -ge 2 ] || fail 'Missing value for --agent'
      agent=$2
      shift 2
      ;;
    --skill)
      [ "$#" -ge 2 ] || fail 'Missing value for --skill'
      skill=$2
      shift 2
      ;;
    --skip-graft-setup)
      skip_graft_setup=true
      shift
      ;;
    --graft-no-global)
      graft_no_global=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --)
      shift
      [ "$#" -le 1 ] || fail 'Only one destination may be specified'
      if [ "$#" -eq 1 ]; then
        destination=$1
        destination_set=true
        shift
      fi
      ;;
    -*) fail "Unknown option: $1" ;;
    *)
      [ "$destination_set" = false ] || fail 'Only one destination may be specified'
      destination=$1
      destination_set=true
      shift
      ;;
  esac
done

case "$agent" in
  all)
    for bundle in .agents .claude .openclaude .zcode; do
      install_bundle "$bundle" "$destination" "$skill"
    done
    ;;
  agents) install_bundle .agents "$destination" "$skill" ;;
  claude) install_bundle .claude "$destination" "$skill" ;;
  openclaude) install_bundle .openclaude "$destination" "$skill" ;;
  zcode) install_bundle .zcode "$destination" "$skill" ;;
  *) fail "Unknown agent: $agent" ;;
esac

graft_installed=false
if [ "$skill" = all ] || [ "$skill" = graft ]; then
  prepare_source
  if [ -d "$SOURCE_ROOT/skills/graft" ]; then
    graft_installed=true
  fi
fi

if [ "$graft_installed" = true ]; then
  if [ "$skip_graft_setup" = true ]; then
    printf '\nSkipped Graft setup (--skip-graft-setup).\n'
  elif [ -n "${HOME:-}" ] && [ "$destination" = "$HOME" ]; then
    printf '\nSkipped Graft setup: destination is $HOME. Run `graft init` inside a repository instead.\n'
  else
    mkdir -p "$destination"
    setup_graft "$destination" "$graft_no_global"
  fi
fi

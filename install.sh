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
Usage: ./install.sh [--agent <agent>] [--skill <skill>] [destination]

Options:
  --agent <agent>  Agent target (default: all)
  --skill <skill>  Skill to install (default: all)
  -h, --help       Show this help

Agents:
  all          Install for every supported agent
  agents       Install to .agents/skills (Zed and Agent Skills clients)
  claude       Install to .claude/skills
  openclaude   Install to .openclaude/skills
  zcode        Install to .zcode/skills

Destination defaults to the current directory.

Examples:
  ./install.sh
  ./install.sh --agent claude /path/to/project
  ./install.sh --skill authula /path/to/project
  ./install.sh --agent claude --skill authula "$HOME"

Remote usage:
  curl -fsSL https://raw.githubusercontent.com/masb0ymas/ai-coding-skills/main/install.sh | sh
  curl -fsSL https://raw.githubusercontent.com/masb0ymas/ai-coding-skills/main/install.sh | sh -s -- --agent claude --skill authula /path/to/project
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
  [ -f "$SOURCE_ROOT/install.sh" ] && [ -d "$SOURCE_ROOT/skills" ] && [ -d "$SOURCE_ROOT/agents" ]
}

prepare_source() {
  if is_repository_root; then
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

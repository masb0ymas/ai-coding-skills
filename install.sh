#!/bin/sh

set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

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
EOF
}

fail() {
  printf '%s\n\n' "$1" >&2
  usage >&2
  exit 1
}

install_bundle() {
  bundle=$1
  destination=$2
  skill=$3
  source_dir="$ROOT_DIR/agents/$bundle/skills"
  target_dir="$destination/$bundle/skills"

  if [ ! -d "$source_dir" ]; then
    printf 'Bundle not found: %s\n' "$source_dir" >&2
    exit 1
  fi

  mkdir -p "$target_dir"

  if [ "$skill" = all ]; then
    cp -R "$source_dir/." "$target_dir/"
    printf 'Installed all skills for %s -> %s\n' "$bundle" "$target_dir"
    return
  fi

  if [ ! -d "$source_dir/$skill" ]; then
    printf 'Skill not found for %s: %s\n' "$bundle" "$skill" >&2
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

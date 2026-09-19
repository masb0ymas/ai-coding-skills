#!/bin/sh

set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SOURCE_DIR="$ROOT_DIR/skills"
LINK_TARGET=../../skills

if [ ! -d "$SOURCE_DIR" ]; then
  printf 'Skills directory not found: %s\n' "$SOURCE_DIR" >&2
  exit 1
fi

for agent in .agents .claude .openclaude .zcode; do
  agent_dir="$ROOT_DIR/agents/$agent"
  skills_path="$agent_dir/skills"

  mkdir -p "$agent_dir"

  if [ -L "$skills_path" ] && [ "$(readlink "$skills_path")" = "$LINK_TARGET" ]; then
    printf 'Already linked agents/%s/skills -> %s\n' "$agent" "$LINK_TARGET"
    continue
  fi

  rm -rf "$skills_path"
  ln -s "$LINK_TARGET" "$skills_path"
  printf 'Linked agents/%s/skills -> %s\n' "$agent" "$LINK_TARGET"
done

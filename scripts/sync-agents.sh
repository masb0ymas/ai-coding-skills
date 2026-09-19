#!/bin/sh

set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SOURCE_DIR="$ROOT_DIR/skills"

if [ ! -d "$SOURCE_DIR" ]; then
  printf 'Skills directory not found: %s\n' "$SOURCE_DIR" >&2
  exit 1
fi

for bundle in .agents .claude .openclaude .zcode; do
  target_dir="$ROOT_DIR/agents/$bundle/skills"
  rm -rf "$target_dir"
  mkdir -p "$target_dir"
  cp -R "$SOURCE_DIR/." "$target_dir/"
  printf 'Synced skills -> agents/%s/skills\n' "$bundle"
done

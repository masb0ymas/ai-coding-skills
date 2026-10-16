#!/usr/bin/env python3
"""Generate a new Go API project with the gofi layer structure.

Copies the gofi template (bundled snapshot, or the latest upstream from GitHub),
renames the Go module and the project name everywhere it appears, and writes a
ready-to-run .env with freshly generated secrets.

Usage:
  python3 scaffold.py --dest ./shop-api --module github.com/acme/shop-api
  python3 scaffold.py --dest ./shop-api --module github.com/acme/shop-api \
      --app-name shop --owner acme --source github --no-release

Only the Python standard library is used. `git` is needed for --source github
and for --git-init.
"""

from __future__ import annotations

import argparse
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

UPSTREAM = "https://github.com/masb0ymas/gofi.git"
SKILL_DIR = Path(__file__).resolve().parent.parent
BUNDLED = SKILL_DIR / "template"

# Upstream files that belong to the gofi repository itself (agent tooling,
# release history, review bots) rather than to a project generated from it.
REPO_SPECIFIC = [
    ".git", ".claude", "graft", "docs", ".omc", ".ignore", "ISSUES.md",
    "CHANGELOG.md", ".coderabbit.yaml", ".mcp.json", "AGENTS.md", "CLAUDE.md",
]
RELEASE_FILES = [".github", "package.json", ".release-it.json"]

TEXT_SUFFIXES = {".go", ".mod", ".md", ".yml", ".yaml", ".json", ".sql", ".example", ".txt", ""}
TEXT_NAMES = {"Makefile", "Dockerfile", ".dockerignore", ".gitignore", ".env.example"}

MODULE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._~\-/]*[A-Za-z0-9]$")
APP_RE = re.compile(r"^[a-z][a-z0-9-]*$")


def die(msg: str) -> None:
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dest", required=True, help="directory to create the project in")
    p.add_argument("--module", required=True, help="Go module path, e.g. github.com/acme/shop-api")
    p.add_argument("--app-name", help="project name (lowercase, digits, '-'); default: last segment of --module")
    p.add_argument("--owner", default="OWNER", help="GitHub owner for the ghcr.io image name in README")
    p.add_argument("--source", choices=["bundled", "github"], default="bundled",
                   help="bundled = pinned snapshot shipped with the skill; github = latest upstream main")
    p.add_argument("--ref", default="main", help="git ref for --source github")
    p.add_argument("--no-release", action="store_true", help="drop the release-it + GitHub Actions release files")
    p.add_argument("--no-env", action="store_true", help="do not write .env with generated secrets")
    p.add_argument("--no-git-init", action="store_true", help="do not run git init")
    p.add_argument("--force", action="store_true", help="allow a non-empty --dest")
    return p.parse_args()


def fetch_source(args: argparse.Namespace, workdir: Path) -> Path:
    if args.source == "bundled":
        if not (BUNDLED / "go.mod").exists():
            die(f"bundled template missing at {BUNDLED}")
        return BUNDLED
    target = workdir / "upstream"
    cmd = ["git", "clone", "--depth", "1", "--branch", args.ref, UPSTREAM, str(target)]
    if subprocess.run(cmd).returncode != 0:
        die("git clone failed; retry with --source bundled")
    return target


def is_text(path: Path) -> bool:
    return path.name in TEXT_NAMES or path.suffix in TEXT_SUFFIXES and path.name != "go.sum"


def rewrite(text: str, path: Path, module: str, app: str, db: str, owner: str, title: str) -> str:
    if path.name == "go.mod":
        return re.sub(r"^module gofi$", f"module {module}", text, count=1, flags=re.M)
    if path.name.startswith("LICENSE"):
        return text  # MIT: the original copyright notice must stay.
    hold = "\x00MODULE\x00"
    if path.suffix == ".go":
        # Import paths first, parked behind a placeholder so the passes below
        # never touch a module path that happens to contain "gofi".
        text = text.replace('"gofi/', f'"{hold}/')
    if path.name == "README.md":
        text = text.replace("# GoFi", f"# {title}", 1)
        text = text.replace("masb0ymas/gofi", f"{owner}/{app}")
    text = text.replace("gofi_test", f"{db}_test")
    # Database names inside DSNs use the underscore form.
    text = re.sub(r"/gofi(?=\?|\s|$|\")", f"/{db}", text)
    text = re.sub(r"dbname=gofi\b", f"dbname={db}", text)
    # Every other bare "gofi" (never "gofiber") is the project name.
    text = re.sub(r"\bgofi\b", app, text)
    return text.replace(hold, module)


def write_env(dest: Path, app: str) -> None:
    example = dest / ".env.example"
    if not example.exists():
        return
    env = example.read_text()
    env = re.sub(r"^APP_SECRET=.*$", f"APP_SECRET={secrets.token_urlsafe(48)}", env, flags=re.M)
    # SUPER_USER needs 12-128 characters; the example value is too short on purpose.
    env = re.sub(r"^SUPER_USER=.*$", f"SUPER_USER=admin@{app}.local:{secrets.token_urlsafe(18)}", env, flags=re.M)
    (dest / ".env").write_text(env)


def main() -> None:
    args = parse_args()
    module = args.module.strip().rstrip("/")
    if not MODULE_RE.match(module):
        die(f"invalid module path {module!r}")
    app = (args.app_name or module.rsplit("/", 1)[-1]).lower()
    if not APP_RE.match(app):
        die(f"app name {app!r} must match {APP_RE.pattern} (pass --app-name)")
    db = app.replace("-", "_")
    title = " ".join(part.capitalize() for part in re.split(r"[-_]", app))

    dest = Path(args.dest).resolve()
    if dest.exists() and any(dest.iterdir()) and not args.force:
        die(f"{dest} is not empty (use --force to write into it)")

    with tempfile.TemporaryDirectory() as tmp:
        src = fetch_source(args, Path(tmp))
        ignore = shutil.ignore_patterns(*REPO_SPECIFIC, *(RELEASE_FILES if args.no_release else []))
        shutil.copytree(src, dest, ignore=ignore, dirs_exist_ok=True)

    changed = 0
    for path in sorted(dest.rglob("*")):
        if not path.is_file() or not is_text(path):
            continue
        old = path.read_text(encoding="utf-8")
        new = rewrite(old, path, module, app, db, args.owner, title)
        if new != old:
            path.write_text(new, encoding="utf-8")
            changed += 1

    leftovers = [str(p.relative_to(dest)) for p in dest.rglob("*.go") if '"gofi/' in p.read_text()]
    if leftovers:
        die(f"imports still reference gofi/: {leftovers}")

    # Renamed literals change column alignment in maps and struct tags.
    if shutil.which("gofmt"):
        subprocess.run(["gofmt", "-w", str(dest)], check=False)

    if not args.no_env:
        write_env(dest, app)
    if not args.no_git_init and shutil.which("git") and not (dest / ".git").exists():
        subprocess.run(["git", "init", "-q", "-b", "main", str(dest)], check=False)

    print(f"created {dest}")
    print(f"  module   {module}")
    print(f"  app name {app}  (database {db})")
    print(f"  source   {args.source}; {changed} files rewritten")
    if not args.no_env:
        print("  .env     written with a random APP_SECRET and SUPER_USER (gitignored)")
    print("\nnext:")
    print(f"  cd {dest}")
    print("  # fill FROM_ADDRESS and RESEND_API_KEY in .env (Authula refuses to start without them)")
    print(f"  docker run -d --name {app}-pg -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB={db} -p 5432:5432 postgres:18")
    print("  go mod tidy && go build ./... && make run")


if __name__ == "__main__":
    main()

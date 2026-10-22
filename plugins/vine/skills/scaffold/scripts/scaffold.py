#!/usr/bin/env python3
"""Generate a new frontend app with the vine structure.

Copies one of the three masb0ymas/vine apps, renames it, and makes it work on
its own (outside the vine monorepo) or as a new package of an existing pnpm
workspace:

  vinext-cf      vinext (Next.js App Router on Vite) deployed to Cloudflare Workers
  vinext-docker  vinext built as a standalone Node server in a Docker image
  vite           Vite SPA with TanStack Router (file routes), served as static files

Usage:
  python3 scaffold.py --dest ./shop-web --variant vinext-cf
  python3 scaffold.py --dest ./apps/admin --variant vite --title "Shop Admin"
  python3 scaffold.py --dest ./shop-web --variant vinext-docker --from ~/code/vine

Only the Python standard library is used. `git` is needed unless --from points
at a local vine checkout.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

UPSTREAM = "https://github.com/masb0ymas/vine.git"
# The commit the plugin's skills were written against; --ref main takes the latest.
PINNED_REF = "953fa11b0c9ad409797eebac94358e7887c912df"

VARIANTS = {"vinext-cf": "vinext-cf", "vinext-docker": "vinext-web", "vite": "vite-web"}

# Build output, caches, local env files and generator metadata that do not
# belong in a new app (--from may point at a working checkout).
IGNORE = ["node_modules", "dist", ".vinext", ".cloudflare", ".wrangler", ".next", ".tanstack", ".cta.json",
          "*.tsbuildinfo", ".env", ".env.local", ".env.*.local", "Dockerfile"]
TEXT_SUFFIXES = {".ts", ".tsx", ".json", ".md", ".html", ".css", ".mjs", ".example", ".yaml", ""}

NAME_RE = re.compile(r"^[a-z][a-z0-9-]*$")
DEPLOY_SCRIPT = Path(__file__).resolve().parents[2] / "deploy" / "scripts" / "apply_deploy.py"

# Workspace detection lives in the deploy script; both must agree on it.
sys.dont_write_bytecode = True
sys.path.insert(0, str(DEPLOY_SCRIPT.parent))
from apply_deploy import workspace_of  # noqa: E402


def die(msg: str) -> None:
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dest", required=True, help="directory to create the app in")
    p.add_argument("--variant", required=True, choices=sorted(VARIANTS), help="which vine app to start from")
    p.add_argument("--name", help="package / worker name (lowercase, digits, '-'); default: --dest folder name")
    p.add_argument("--title", help="display name (browser title, VITE_/NEXT_PUBLIC_APP_NAME); default from --name")
    p.add_argument("--ref", default=PINNED_REF, help="git ref (branch, tag or commit) of masb0ymas/vine")
    p.add_argument("--from", dest="source", help="use a local vine checkout instead of cloning")
    p.add_argument("--no-git-init", action="store_true", help="do not run git init")
    p.add_argument("--force", action="store_true", help="allow a non-empty --dest")
    return p.parse_args()


def fetch(ref: str, workdir: Path) -> Path:
    # init + fetch (rather than clone --branch) so a commit sha works as --ref too.
    target = workdir / "vine"
    steps = [
        ["git", "init", "-q", str(target)],
        ["git", "-C", str(target), "fetch", "-q", "--depth", "1", UPSTREAM, ref],
        ["git", "-C", str(target), "checkout", "-q", "FETCH_HEAD"],
    ]
    for cmd in steps:
        if subprocess.run(cmd).returncode != 0:
            die(f"{' '.join(cmd)} failed; check network access or pass --from <local vine checkout>")
    return target


def rewrite_text(paths: list[Path], old: str, name: str, title: str) -> int:
    changed = 0
    for path in paths:
        if path.suffix not in TEXT_SUFFIXES or path.name == "routeTree.gen.ts":
            continue
        text = path.read_text(encoding="utf-8")
        new = re.sub(rf"(?<![\w-]){re.escape(old)}(?![\w-])", name, text)
        # Functions as replacements: a title may contain backslashes.
        new = re.sub(r"^VITE_APP_NAME=.*$", lambda _: f"VITE_APP_NAME={title}", new, flags=re.M)
        if path.name == "index.html":
            new = re.sub(r"<title>[^<]*</title>", lambda _: f"<title>{html.escape(title)}</title>", new, count=1)
        if path.name == "layout.tsx" and path.parent.name == "app":
            ts = title.replace("\\", "\\\\").replace("'", "\\'")
            new = re.sub(r"title: '[^']*'", lambda _: f"title: '{ts}'", new, count=1)
        if new != text:
            path.write_text(new, encoding="utf-8")
            changed += 1
    return changed


def write_standalone_files(src_root: Path, dest: Path) -> None:
    """Carry over what the app inherited from the vine monorepo root."""
    root_pkg = json.loads((src_root / "package.json").read_text())
    pkg_path = dest / "package.json"
    pkg = json.loads(pkg_path.read_text())
    if "packageManager" in root_pkg:
        pkg["packageManager"] = root_pkg["packageManager"]
    pkg_path.write_text(json.dumps(pkg, indent=2) + "\n")

    # pnpm 10+ blocks dependency build scripts unless allowed; esbuild, workerd,
    # lightningcss and sharp need theirs. A settings-only workspace file is enough.
    ws = (src_root / "pnpm-workspace.yaml").read_text()
    allow = ws[ws.find("allowBuilds:"):] if "allowBuilds:" in ws else ""
    if allow:
        (dest / "pnpm-workspace.yaml").write_text(allow.rstrip() + "\n")


def write_env_example(dest: Path, variant: str, title: str) -> None:
    if variant == "vite":
        return  # vite-web ships its own .env.example
    (dest / ".env.example").write_text(
        f"NEXT_PUBLIC_APP_NAME={title}\n"
        "# Empty = same origin; next.config.ts rewrites /api to API_PROXY_TARGET.\n"
        "NEXT_PUBLIC_API_URL=\n"
        "# Read at build time by next.config.ts (default http://localhost:8080).\n"
        "API_PROXY_TARGET=\n"
    )


def write_readme(dest: Path, variant: str, name: str, title: str, in_workspace: bool) -> None:
    run = "pnpm" if not in_workspace else f"pnpm --filter {name}"
    lines = [f"# {title}", "", f"Frontend generated from [masb0ymas/vine](https://github.com/masb0ymas/vine) (`{variant}`).", ""]
    lines += ["## Scripts", "", f"- `{run} dev` starts the dev server (proxies `/api` to the backend on :8080).", f"- `{run} build` builds production output."]
    if variant == "vinext-cf":
        lines += [f"- `{run} start` previews the built Worker locally.", f"- `{run} run deploy` deploys to Cloudflare Workers (`cf auth login` or `CLOUDFLARE_API_TOKEN`)."]
    elif variant == "vinext-docker":
        lines += [f"- `{run} start` runs the production server locally.", "- `docker build -t " + name + " .` builds the image (see the Dockerfile header)."]
    else:
        lines += [f"- `{run} preview` serves the built SPA locally.", f"- `{run} generate-routes` regenerates `src/routeTree.gen.ts`."]
    lines += ["", "Environment variables are documented in `.env.example`.", ""]
    (dest / "README.md").write_text("\n".join(lines))


def main() -> None:
    args = parse_args()
    dest = Path(args.dest).resolve()
    name = (args.name or dest.name).lower()
    if not NAME_RE.match(name):
        die(f"name {name!r} must match {NAME_RE.pattern} (pass --name)")
    title = args.title or " ".join(part.capitalize() for part in name.split("-"))
    if dest.exists() and any(dest.iterdir()) and not args.force:
        die(f"{dest} is not empty (use --force to write into it)")

    app_dir = VARIANTS[args.variant]
    workspace = workspace_of(dest)
    copied: list[Path] = []

    def copy(src_file: str, dst_file: str) -> None:
        target = Path(dst_file)
        if target.exists():
            print(f"  overwrite {target.relative_to(dest)}")
        shutil.copy2(src_file, dst_file)
        copied.append(target)

    with tempfile.TemporaryDirectory() as tmp:
        src_root = Path(args.source).expanduser().resolve() if args.source else fetch(args.ref, Path(tmp))
        src = src_root / "apps" / app_dir
        if not (src / "package.json").exists():
            die(f"{src} is not a vine app (expected apps/{app_dir}/package.json)")
        # The upstream Dockerfile (ignored above) assumes the vine monorepo; the
        # deploy skill writes one that matches where this app actually lives.
        shutil.copytree(src, dest, ignore=shutil.ignore_patterns(*IGNORE), copy_function=copy, dirs_exist_ok=True)
        if workspace is None:
            write_standalone_files(src_root, dest)

    # Only files that came from upstream are renamed; anything already in dest
    # (a .git folder, the user's files under --force) is left alone.
    changed = rewrite_text(copied, app_dir, name, title)
    write_env_example(dest, args.variant, title)
    gitignore = dest / ".gitignore"
    if gitignore.exists() and re.search(r"^\.env\*", gitignore.read_text(), re.M) and "!.env.example" not in gitignore.read_text():
        # Upstream ignores .env*, which would keep the documented example out of git.
        gitignore.write_text(gitignore.read_text().rstrip("\n") + "\n!.env.example\n")
    write_readme(dest, args.variant, name, title, workspace is not None)

    if args.variant == "vinext-docker":
        subprocess.run([sys.executable, str(DEPLOY_SCRIPT), "--root", str(dest), "--target", "docker"], check=True)
    if not args.no_git_init and workspace is None and shutil.which("git") and not (dest / ".git").exists():
        subprocess.run(["git", "init", "-q", "-b", "main", str(dest)], check=False)

    print(f"created {dest}")
    print(f"  variant  {args.variant} (from apps/{app_dir} @ {args.source or args.ref})")
    print(f"  name     {name}  title {title!r}; {changed} files renamed")
    print(f"  layout   {'package of pnpm workspace ' + str(workspace) if workspace else 'standalone project'}")
    if workspace and "allowBuilds:" not in (workspace / "pnpm-workspace.yaml").read_text():
        print("  note     pnpm-workspace.yaml has no allowBuilds; esbuild, lightningcss, workerd and sharp need")
        print("           their install scripts (see apps' upstream pnpm-workspace.yaml)")
    print("\nnext:")
    if workspace:
        print(f"  cd {workspace} && pnpm install && pnpm --filter {name} dev")
    else:
        print(f"  cd {dest} && pnpm install && pnpm dev")
    print("  # the app expects the API on http://localhost:8080 under /api/v1 (see .env.example)")


if __name__ == "__main__":
    main()

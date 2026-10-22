#!/usr/bin/env python3
"""Write the deploy files for a vine-style frontend.

  --target docker      vinext app -> Node standalone server image
                       vite app   -> static SPA in an nginx image that proxies /api
  --target cloudflare  vinext-cf app -> GitHub Actions workflow running `pnpm run deploy`

The app may be a standalone project or a package inside a pnpm workspace; the
Dockerfile and workflow are written to match. Re-running is safe: identical
files are skipped and a changed file is kept as <file>.bak before overwriting.

Usage:
  python3 apply_deploy.py --root . --target docker
  python3 apply_deploy.py --root apps/web --target cloudflare --branch main
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import sys
from pathlib import Path

NODE_IMAGE = "node:24-alpine"
NGINX_IMAGE = "nginxinc/nginx-unprivileged:1.29-alpine"

DOCKERIGNORE = """\
**/node_modules
**/dist
**/.vinext
**/.cloudflare
**/.wrangler
**/.env*
!**/.env.example
.git
"""

VINEXT_DOCKERFILE = """\
# {build_hint}
FROM {node} AS build
WORKDIR {workdir}
RUN corepack enable
# Resolved at build time: next.config.ts reads API_PROXY_TARGET for the /api
# rewrite and NEXT_PUBLIC_* are inlined into the browser bundle, so changing
# them means rebuilding the image.
ARG API_PROXY_TARGET
ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_APP_NAME
{install}

FROM {node}
WORKDIR /app
# vinext binds to HOST (not Next.js' HOSTNAME, which Linux already sets).
ENV NODE_ENV=production PORT=3000 HOST=0.0.0.0
COPY --from=build {workdir}/{app_rel}dist/standalone .
USER node
EXPOSE 3000
# /sign-in renders on the server without a session, so it proves SSR works.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \\
  CMD node -e "fetch('http://127.0.0.1:3000/sign-in').then(r=>process.exit(r.ok?0:1),()=>process.exit(1))"
CMD ["node", "server.js"]
"""

VITE_DOCKERFILE = """\
# {build_hint}
FROM {node} AS build
WORKDIR {workdir}
RUN corepack enable
# Vite inlines VITE_* into the bundle at build time; leave VITE_API_URL empty
# to call the API on the same origin through the nginx /api proxy below.
ARG VITE_API_URL
ARG VITE_APP_NAME
{install}

FROM {nginx}
# Where nginx proxies /api; must resolve when the container starts.
ENV API_UPSTREAM=http://api:8080
COPY {app_rel}deploy/nginx/default.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build {workdir}/{app_rel}dist /usr/share/nginx/html
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD wget -qO /dev/null http://127.0.0.1:8080/ || exit 1
"""

NGINX_CONF = """\
# SPA server: static files + reverse proxy to the API on the same origin.
# ${API_UPSTREAM} is filled from the environment when the container starts.

server {
    listen 8080;
    server_name _;
    root /usr/share/nginx/html;

    client_max_body_size 10m;

    gzip on;
    gzip_types text/css application/javascript application/json image/svg+xml;

    # The header is replaced, not appended to: an API that reads the first
    # X-Forwarded-For entry would otherwise trust a client-sent value. Behind
    # another load balancer, use the realip module so $remote_addr is the client.
    location /api/ {
        proxy_pass ${API_UPSTREAM};
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 35s;
    }

    # Content-hashed bundles: safe to cache for a year; a miss is a real 404.
    location /assets/ {
        add_header Cache-Control "public, max-age=31536000, immutable";
        try_files $uri =404;
    }

    # Everything else: the file if it exists, otherwise the app shell for
    # TanStack Router. The shell is never cached, so a deploy is picked up on
    # the next navigation.
    location / {
        add_header Cache-Control "no-cache";
        try_files $uri $uri/ /index.html;
    }
}
"""

CF_WORKFLOW = """\
# Deploys {name} to Cloudflare Workers.
# Repository secret: CLOUDFLARE_API_TOKEN (Workers Scripts: Edit, plus Images
# if the IMAGES binding is used). Repository variables, read at build time:
# API_PROXY_TARGET (where /api is proxied) or NEXT_PUBLIC_API_URL (API origin)
# - one of them is required - and optionally NEXT_PUBLIC_APP_NAME.

name: Deploy {name}

on:
  push:
    branches: [{branch}]{paths}
  workflow_dispatch:

concurrency:
  group: deploy-{name}
  cancel-in-progress: false

permissions:
  contents: read

jobs:
  deploy:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: {app_dir}
    steps:
      - uses: actions/checkout@v5
      - uses: pnpm/action-setup@v4
        with:
          package_json_file: {pm_package_json}
      - uses: actions/setup-node@v5
        with:
          node-version: 24
          cache: pnpm
          cache-dependency-path: {lockfile}
      # An unset variable is "" here, which next.config.ts's `??` fallback does
      # not catch: /api would rewrite to itself.
      - name: require an API target
        run: test -n "$API_PROXY_TARGET$NEXT_PUBLIC_API_URL" || {{ echo "set the API_PROXY_TARGET or NEXT_PUBLIC_API_URL repository variable"; exit 1; }}
        env:
          API_PROXY_TARGET: ${{{{ vars.API_PROXY_TARGET }}}}
          NEXT_PUBLIC_API_URL: ${{{{ vars.NEXT_PUBLIC_API_URL }}}}
      - run: pnpm install --frozen-lockfile
      - run: pnpm run deploy
        env:
          CLOUDFLARE_API_TOKEN: ${{{{ secrets.CLOUDFLARE_API_TOKEN }}}}
          API_PROXY_TARGET: ${{{{ vars.API_PROXY_TARGET }}}}
          NEXT_PUBLIC_API_URL: ${{{{ vars.NEXT_PUBLIC_API_URL }}}}
          NEXT_PUBLIC_APP_NAME: ${{{{ vars.NEXT_PUBLIC_APP_NAME }}}}
"""


def die(msg: str) -> None:
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def is_workspace_root(path: Path) -> bool:
    ws = path / "pnpm-workspace.yaml"
    return ws.exists() and re.search(r"^packages:", ws.read_text(), re.M) is not None


def workspace_of(root: Path) -> Path | None:
    """Nearest workspace whose `packages:` globs include root."""
    for parent in root.parents:
        if not is_workspace_root(parent):
            continue
        globs, inside = [], False
        for line in (parent / "pnpm-workspace.yaml").read_text().splitlines():
            if re.match(r"^packages:\s*$", line):
                inside = True
            elif inside and re.match(r"^\s*-\s*", line):
                globs.append(line.split("-", 1)[1].strip().strip("'\"").rstrip("/"))
            elif inside and line.strip() and not line.startswith((" ", "#")):
                break
        rel = root.relative_to(parent).as_posix()
        if any(fnmatch.fnmatch(rel, g) for g in globs if not g.startswith("!")):
            return parent
    return None


def detect_kind(root: Path) -> str:
    pkg = json.loads((root / "package.json").read_text())
    deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
    if "vinext" in deps:
        return "vinext-cf" if (root / "cloudflare.config.ts").exists() else "vinext"
    if "@tanstack/react-router" in deps:
        return "vite"
    die("neither vinext nor @tanstack/react-router in package.json; is this a vine app?")
    return ""


def write(path: Path, content: str) -> None:
    if path.exists():
        old = path.read_text()
        if old == content:
            print(f"  same     {path}")
            return
        path.with_name(path.name + ".bak").write_text(old)
        print(f"  replaced {path} (old kept as {path.name}.bak)")
    else:
        print(f"  created  {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def ensure_standalone(root: Path) -> None:
    cfg = root / "next.config.ts"
    text = cfg.read_text()
    if re.search(r"output:\s*['\"]standalone['\"]", text):
        return
    new, n = re.subn(r"(const nextConfig: NextConfig = \{\n)", r"\1  output: 'standalone',\n", text, count=1)
    if n == 0:
        die(f"add output: 'standalone' to {cfg} by hand (could not find the nextConfig object)")
    cfg.write_text(new)
    print(f"  updated  {cfg} (output: 'standalone')")


def docker(root: Path, kind: str, name: str, slug: str) -> None:
    if kind == "vinext-cf":
        die("this app targets Cloudflare (cloudflare.config.ts); use --target cloudflare, "
            "or start from the vinext-docker variant for a Node image")
    ws = workspace_of(root)
    if ws:
        rel = root.relative_to(ws).as_posix() + "/"
        hint = f"Build from the workspace root: docker build -f {rel}Dockerfile -t {slug} ."
        # `name...` installs the app and the workspace packages it depends on.
        install = (f"COPY . .\nRUN pnpm install --frozen-lockfile --filter {name}...\n"
                   f"RUN pnpm --filter {name} build")
        workdir, ignore_at = "/repo", ws
    else:
        if not (root / "pnpm-lock.yaml").exists():
            print("  note     no pnpm-lock.yaml yet: run `pnpm install` and commit it before docker build")
        rel, hint = "", f"docker build -t {slug} ."
        # Manifests first so the dependency layer is cached across source edits.
        install = ("COPY package.json pnpm-lock.yaml pnpm-workspace.yaml* ./\n"
                   "RUN pnpm install --frozen-lockfile\nCOPY . .\nRUN pnpm build")
        workdir, ignore_at = "/app", root

    fmt = dict(build_hint=hint, node=NODE_IMAGE, nginx=NGINX_IMAGE, workdir=workdir, app_rel=rel, install=install)
    if kind == "vinext":
        ensure_standalone(root)
        write(root / "Dockerfile", VINEXT_DOCKERFILE.format(**fmt))
    else:
        write(root / "Dockerfile", VITE_DOCKERFILE.format(**fmt))
        write(root / "deploy" / "nginx" / "default.conf.template", NGINX_CONF)
    if not (ignore_at / ".dockerignore").exists():
        write(ignore_at / ".dockerignore", DOCKERIGNORE)


def cloudflare(root: Path, kind: str, name: str, slug: str, branch: str) -> None:
    if kind != "vinext-cf":
        die("--target cloudflare needs a vinext app with cloudflare.config.ts (the vinext-cf variant)")
    git_root = next((p for p in (root, *root.parents) if (p / ".git").exists()), None)
    if git_root is None:
        die("no git repository found; run `git init` first (the workflow lives at the git root)")
    ws = workspace_of(root)
    pm_root = ws or root
    if git_root not in (pm_root, *pm_root.parents):
        die(f"the pnpm root {pm_root} is outside the git repository {git_root}")
    rel = lambda p: p.relative_to(git_root).as_posix() or "."  # noqa: E731
    app_dir = rel(root)
    # A workspace app also changes through sibling packages and the shared
    # lockfile, so only a standalone app in a subfolder gets a paths filter.
    paths = "" if ws or app_dir == "." else f'\n    paths: ["{app_dir}/**", ".github/workflows/**"]'
    content = CF_WORKFLOW.format(
        name=slug, branch=branch, paths=paths, app_dir=app_dir,
        pm_package_json=f"{rel(pm_root)}/package.json".removeprefix("./"),
        lockfile=f"{rel(pm_root)}/pnpm-lock.yaml".removeprefix("./"),
    )
    write(git_root / ".github" / "workflows" / f"deploy-{slug}.yml", content)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--root", default=".", help="the app directory (holds package.json)")
    p.add_argument("--target", required=True, choices=["docker", "cloudflare"])
    p.add_argument("--branch", default="main", help="branch that triggers the Cloudflare deploy workflow")
    args = p.parse_args()

    root = Path(args.root).resolve()
    if not (root / "package.json").exists():
        die(f"no package.json in {root}")
    if is_workspace_root(root):
        die(f"{root} is the workspace root; pass the app folder, e.g. --root apps/web")
    kind = detect_kind(root)
    # Scoped names (@acme/web) are fine for pnpm --filter but not as a file
    # or image name.
    name = json.loads((root / "package.json").read_text())["name"]
    slug = re.sub(r"[^a-z0-9-]+", "-", name.lower().lstrip("@")).strip("-")
    print(f"{kind} app {name} at {root}")
    if args.target == "docker":
        docker(root, kind, name, slug)
    else:
        cloudflare(root, kind, name, slug, args.branch)


if __name__ == "__main__":
    main()

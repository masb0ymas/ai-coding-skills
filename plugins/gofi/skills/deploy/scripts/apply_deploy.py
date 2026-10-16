#!/usr/bin/env python3
"""Set up container deployment for a gofi project.

Modes:
  api        backend only: Dockerfile (api + migrate + healthcheck), HEALTHCHECK
  embedded   backend serves the SPA too: Dockerfile builds the SPA with Node and
             copies it into the image (SPA_DIR=/app/web); adds the SPA
             middleware, SPA_DIR config/flag, mounts it after the API routes
  separate   backend image (as api) + Dockerfile.web: nginx image serving the
             SPA and proxying /v1 and /health to the API

Common: cmd/healthcheck (probe for the shell-less distroless image),
.dockerignore entries, optional docker-compose.yml (--compose).
Existing files that would be replaced are kept as <name>.bak.

usage:
  python3 apply_deploy.py --root . --mode embedded --web-dir web --web-out dist --compose
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
ASSETS = SKILL / "assets"

changes: list[str] = []
notes: list[str] = []


def die(msg: str) -> None:
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def write(root: Path, rel: str, content: str, backup: bool = True) -> None:
    dst = root / rel
    if dst.exists():
        old = dst.read_text()
        if old == content:
            return
        if backup:
            shutil.copy2(dst, dst.with_name(dst.name + ".bak"))
            changes.append(f"M {rel}  (previous kept as {rel}.bak)")
        else:
            changes.append(f"M {rel}")
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)
        changes.append(f"A {rel}")
    dst.write_text(content)


def copy_if_missing(root: Path, asset: str, rel: str) -> None:
    dst = root / rel
    if dst.exists():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ASSETS / asset, dst)
    changes.append(f"A {rel}")


def patch(root: Path, rel: str, fn, marker: str) -> None:
    """Apply fn(text) -> text unless marker is already present."""
    p = root / rel
    if not p.exists():
        notes.append(f"{rel} not found; apply its change by hand (see references/deploy.md)")
        return
    text = p.read_text()
    if marker in text:
        return
    new = fn(text)
    if new is None or new == text:
        notes.append(f"{rel}: expected code not found; apply the change by hand (see references/deploy.md)")
        return
    p.write_text(new)
    changes.append(f"M {rel}")


def app_name(root: Path) -> str:
    env = root / ".env.example"
    if env.exists():
        m = re.search(r"^APP_NAME=(\S+)", env.read_text(), re.M)
        if m:
            return m.group(1)
    mod = re.search(r"^module\s+(\S+)", (root / "go.mod").read_text(), re.M).group(1)
    return mod.rsplit("/", 1)[-1].lower()


# --------------------------------------------------------------------------- #
# Go patches for the embedded mode
# --------------------------------------------------------------------------- #

def patch_config(t: str) -> str | None:
    m = re.search(r"type ConfigApp struct \{\n(.*?)\n\}", t, re.S)
    if not m:
        return None
    field = "\t// SPADir is the build output of a single-page app served at /; empty\n\t// disables it.\n\tSPADir string"
    return t[:m.end() - 2] + "\n" + field + t[m.end() - 2:]


def patch_flag(t: str) -> str | None:
    anchor = re.search(r"^\tflag\.StringVar\(&cfg\.App\.TrustedProxies.*\n", t, re.M)
    if not anchor:
        anchor = re.search(r"^\t// Database\n", t, re.M)
        if not anchor:
            return None
        pos = anchor.start()
    else:
        pos = anchor.end()
    line = ('\n\t// SPA\n\tflag.StringVar(&cfg.App.SPADir, "spa-dir", envString("SPA_DIR", ""), '
            '"Directory of a built single-page app served at / (empty disables)")\n')
    return t[:pos] + line + t[pos:]


SPA_MOUNT = """\troutes(server, app)

	// The SPA answers whatever the API routes did not: its built files, then
	// index.html for client-side routes. /v1 and /health stay API-only.
	if dir := app.Config.App.SPADir; dir != "" {
		spa, err := middlewares.SPA(middlewares.SPAConfig{
			FS:      os.DirFS(dir),
			Exclude: []string{"/v1", "/health"},
		})
		if err != nil {
			return nil, err
		}
		server.Use(spa)
	}
"""

HELMET = """\tserver.Use(helmet.New(helmet.Config{
		// The default require-corp blocks cross-origin images, fonts and
		// scripts an SPA loads from a CDN; the API's JSON is unaffected.
		CrossOriginEmbedderPolicy: "unsafe-none",
	}))
"""


def patch_server(t: str) -> str | None:
    if "\troutes(server, app)\n" not in t:
        return None
    t = t.replace("\troutes(server, app)\n", SPA_MOUNT, 1)
    t = t.replace("\tserver.Use(helmet.New())\n", HELMET, 1)
    if '"os"' not in t:
        t = t.replace("import (\n", 'import (\n\t"os"\n', 1)
    return t


def patch_routes(t: str) -> str | None:
    m = re.search(r'^\tr\.Get\("/", func\(c fiber\.Ctx\) error \{\n.*?^\t\}\)\n', t, re.S | re.M)
    if not m:
        return None
    block = "".join("\t" + line if line.strip() else line for line in m.group(0).splitlines(True))
    wrapped = "\t// With an SPA, / is its index.html (see server.go).\n\tif app.Config.App.SPADir == \"\" {\n" + block + "\t}\n"
    return t[:m.start()] + wrapped + t[m.end():]


def patch_env(t: str) -> str:
    line = ("\n# Directory of a built single-page app served at / by the API (the\n"
            "# fullstack image sets /app/web). Empty disables it.\nSPA_DIR=\n")
    anchor = t.find("# Apply embedded migrations")
    return t + line if anchor < 0 else t[:anchor] + line.lstrip("\n") + "\n" + t[anchor:]


# --------------------------------------------------------------------------- #

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".")
    ap.add_argument("--mode", choices=["api", "embedded", "separate"], required=True)
    ap.add_argument("--web-dir", default="web", help="SPA project folder in the repo (embedded/separate)")
    ap.add_argument("--web-out", default="dist", help="SPA build output folder, relative to --web-dir")
    ap.add_argument("--compose", action="store_true", help="write docker-compose.yml")
    ap.add_argument("--no-dockerfile", action="store_true", help="leave Dockerfile untouched")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    if not (root / "go.mod").exists() or not (root / "cmd/api").is_dir():
        die(f"{root} does not look like a gofi project (go.mod + cmd/api)")
    spa_mode = args.mode in ("embedded", "separate")
    if spa_mode and not (root / args.web_dir / "package.json").exists():
        notes.append(f"{args.web_dir}/package.json not found: put the SPA project there before building the image")

    copy_if_missing(root, "go/cmd/healthcheck/main.go", "cmd/healthcheck/main.go")

    if not args.no_dockerfile:
        src = "Dockerfile.fullstack" if args.mode == "embedded" else "Dockerfile.api"
        df = (ASSETS / "docker" / src).read_text()
        df = df.replace("ARG WEB_DIR=web", f"ARG WEB_DIR={args.web_dir}").replace("ARG WEB_OUT=dist", f"ARG WEB_OUT={args.web_out}")
        write(root, "Dockerfile", df)
    if args.mode == "separate":
        df = (ASSETS / "docker/Dockerfile.web").read_text()
        df = df.replace("ARG WEB_DIR=web", f"ARG WEB_DIR={args.web_dir}").replace("ARG WEB_OUT=dist", f"ARG WEB_OUT={args.web_out}")
        write(root, "Dockerfile.web", df)
        write(root, "deploy/nginx/default.conf.template", (ASSETS / "nginx/default.conf.template").read_text())
        notes.append("set TRUSTED_PROXIES on the API to the nginx container's network so rate limits see real client IPs")

    di = root / ".dockerignore"
    existing = di.read_text() if di.exists() else ""
    wanted = ["**/node_modules"] + ([f"{args.web_dir}/{args.web_out}"] if spa_mode else [])
    missing = [w for w in wanted if w not in existing.splitlines()]
    if missing:
        block = "\n# SPA dependencies and output are produced inside the image build.\n" + "\n".join(missing) + "\n"
        di.write_text(existing.rstrip("\n") + "\n" + block)
        changes.append("M .dockerignore")

    if args.mode == "embedded":
        copy_if_missing(root, "go/internal/middlewares/spa.go", "internal/middlewares/spa.go")
        copy_if_missing(root, "go/internal/middlewares/spa_test.go", "internal/middlewares/spa_test.go")
        patch(root, "internal/config/config.go", patch_config, "SPADir")
        patch(root, "cmd/api/flag.go", patch_flag, "SPADir")
        patch(root, "cmd/api/server.go", patch_server, "middlewares.SPA(")
        patch(root, "cmd/api/routes.go", patch_routes, "SPADir")
        patch(root, ".env.example", patch_env, "SPA_DIR")
        notes.append(f"local dev: build the SPA (cd {args.web_dir} && npm run build) and set SPA_DIR={args.web_dir}/{args.web_out}")

    if args.compose:
        app = app_name(root)
        compose = (ASSETS / "compose/docker-compose.yml").read_text()
        compose = compose.replace("__APP__", app).replace("__DB__", app.replace("-", "_"))
        if args.mode != "separate":
            compose = re.sub(r"\n  web:\n.*?(?=\nvolumes:)", "\n", compose, flags=re.S)
            compose = compose.replace(
                "#   docker compose --profile web up -d --build   # + separate SPA server on :3000\n", "")
        write(root, "docker-compose.yml", compose)

    go_files = [str(root / c.split()[1]) for c in changes if c.split()[1].endswith(".go")]
    if go_files and shutil.which("gofmt"):
        subprocess.run(["gofmt", "-w", *go_files], check=False)

    print(f"deploy mode: {args.mode}")
    for c in changes or ["(nothing to change)"]:
        print(f"  {c}")
    for n in notes:
        print(f"note: {n}")
    print("\nnext: go build ./... && go test ./... && docker build -t app .")


if __name__ == "__main__":
    main()

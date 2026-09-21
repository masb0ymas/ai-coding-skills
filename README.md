# AI Coding Skills

A collection of portable [Agent Skills](https://agentskills.io/) for AI coding agents. Each skill contains a `SKILL.md` file and optional supporting resources that agents load only when relevant.

## Supported agents

| Target | Project directory | `--target` value |
| --- | --- | --- |
| Zed / Agent Skills-compatible clients | `.agents/skills/` | `agents` |
| Claude Code | `.claude/skills/` | `claude` |
| OpenClaude | `.openclaude/skills/` | `openclaude` |
| Zcode | `.zcode/skills/` | `zcode` |

## Quick start

### Install directly from GitHub

You can run the installer without cloning this repository. The installer downloads the latest `main` branch and installs all skills for all supported agents into the current directory:

```sh
curl -fsSL https://raw.githubusercontent.com/masb0ymas/ai-coding-skills/main/install.sh | sh
```

Install into a specific project:

```sh
curl -fsSL https://raw.githubusercontent.com/masb0ymas/ai-coding-skills/main/install.sh \
  | sh -s -- /path/to/project
```

Install for one agent only:

```sh
curl -fsSL https://raw.githubusercontent.com/masb0ymas/ai-coding-skills/main/install.sh \
  | sh -s -- --target claude /path/to/project
```

Install one skill for one agent:

```sh
curl -fsSL https://raw.githubusercontent.com/masb0ymas/ai-coding-skills/main/install.sh \
  | sh -s -- --target claude --skill authula /path/to/project
```

Arguments passed to a piped shell must come after `sh -s --`.

> Review remote scripts before piping them into a shell. You can download the installer first, inspect it, and then run it:
>
> ```sh
> curl -fsSLO https://raw.githubusercontent.com/masb0ymas/ai-coding-skills/main/install.sh
> less install.sh
> sh install.sh --target claude --skill authula /path/to/project
> ```

Remote installation requires `curl` or `wget`, plus `tar`.

### Install from a local clone

Clone or download this repository, then run the installer from the repository root.

Install all skills for all agents:

```sh
./install.sh /path/to/project
```

Select one agent with `--target`:

```sh
./install.sh --target claude /path/to/project
./install.sh --target agents /path/to/project
./install.sh --target openclaude /path/to/project
./install.sh --target zcode /path/to/project
```

Select one skill with `--skill`. Without `--target`, the selected skill is installed for every supported agent:

```sh
./install.sh --skill authula /path/to/project
```

Select an agent and a skill together:

```sh
./install.sh --target claude --skill authula /path/to/project
```

When run without arguments, the installer installs all skills for all agents into the current directory:

```sh
cd /path/to/project
/path/to/ai-coding-skills/install.sh
```

The installer copies skills into the target directories without removing other installed skills.

### Install globally

Use your home directory as the destination:

```sh
./install.sh "$HOME"
```

Or install a specific skill for one agent:

```sh
./install.sh --target claude --skill authula "$HOME"
```

The same operation can be run remotely:

```sh
curl -fsSL https://raw.githubusercontent.com/masb0ymas/ai-coding-skills/main/install.sh \
  | sh -s -- --target claude --skill authula "$HOME"
```

> Global locations depend on the agent. Claude Code uses `~/.claude/skills/`, while Zed and compatible Agent Skills clients can use `~/.agents/skills/`.

## Installer reference

```text
Usage: ./install.sh [--target <agent>] [--skill <skill>] [--skip-graft-setup] [--graft-no-global] [destination]
```

| Option | Description | Default |
| --- | --- | --- |
| `--target <agent>` | Target `all`, `agents`, `claude`, `openclaude`, or `zcode` | `all` |
| `--skill <skill>` | Install all skills or one skill by directory name | `all` |
| `--skip-graft-setup` | Copy graft skill files only; skip CLI install, `graft init`, and verification | Disabled |
| `--graft-no-global` | Pass `--no-global` to `graft init` for repo-only wiring | Disabled |
| `-h`, `--help` | Show command help | — |
| `destination` | Project or home directory into which agent folders are installed | Current directory |

### Graft skill setup

Installing the `graft` skill (either explicitly or as part of `--skill all`) also runs the operational setup in the destination:

1. Install the Graft CLI unless it is already available:

   ```sh
   npm install -g @nanonets/graft
   ```

2. Build the context graph and wire it into Claude Code:

   ```sh
   cd /path/to/project
   graft init -y
   ```

   Add `--graft-no-global` to the installer when you want repo-only wiring:

   ```sh
   ./install.sh --skill graft --graft-no-global /path/to/project
   ```

3. Verify that `graft/` was created and report how many map files it built.

Use `--skip-graft-setup` for skills-only installation without touching npm or running Graft:

```sh
./install.sh --skill graft --skip-graft-setup /path/to/project
```

Graft setup is skipped automatically when the destination is `$HOME`, because global installs are not repositories.

## Available skills

| Skill | What it does |
| --- | --- |
| [`authula`](docs/authula/README.md) | Builds authentication with Authula, the open-source, plugin-based Go auth framework: library and standalone modes, plugins, route mappings, hooks, and custom plugins. |
| [`graft`](docs/graft/README.md) | Repo-context workflow for repositories initialized with Graft: a linked-markdown graph plus call graphs for finding code, tracing callers, and scoping edits with minimal token use. |
| [`humanizer`](docs/humanizer/README.md) | Rewrites AI-sounding text so it reads like a person wrote it, without changing what it says. Built on Wikipedia's "Signs of AI writing". |
| [`postgres-best-practices`](docs/postgres-best-practices/README.md) | Best practices for PostgreSQL 14 through 18: schema design, indexing, query optimization, diagnostics, replication, backup and restore, security, and upgrades. |
| [`typesafe-ai`](docs/typesafe-ai/README.md) | Builds AI-powered software with TypeSafe System One models: typed judgments and probabilities that code can combine, for routing, ranking, extraction, and verification. |
| [`ui-ux-pro-max`](docs/ui-ux-pro-max/README.md) | UI/UX design intelligence with searchable local catalogs: styles, product palettes, font pairings, UX guidelines, icons, motion presets, chart types, and 22 technology stacks. |
| [`ui-styling`](docs/ui-styling/README.md) | Accessible interfaces with shadcn/ui, Tailwind CSS, theming, dark mode, and canvas-based visual design. |

Each reference page documents when the skill activates, what it covers, how it works, every file it ships, and example prompts. Install any single skill the same way:

```sh
./install.sh --target claude --skill humanizer /path/to/project
```

## Repository structure

```text
.
├── docs/                            # Per-skill reference documentation
│   ├── authula/README.md
│   ├── graft/README.md
│   ├── humanizer/README.md
│   ├── postgres-best-practices/README.md
│   ├── typesafe-ai/README.md
│   ├── ui-ux-pro-max/README.md
│   └── ui-styling/README.md
├── skills/                          # Canonical source for every skill
│   ├── authula/
│   │   ├── SKILL.md
│   │   └── references/
│   ├── graft/
│   │   └── SKILL.md
│   ├── humanizer/
│   │   ├── LICENSE
│   │   └── SKILL.md
│   ├── postgres-best-practices/
│   │   ├── SKILL.md
│   │   └── references/
│   ├── typesafe-ai/
│   │   ├── LICENSE
│   │   └── SKILL.md
│   ├── ui-ux-pro-max/
│   │   ├── LICENSE
│   │   ├── SKILL.md
│   │   ├── data/
│   │   ├── references/
│   │   └── scripts/
│   └── ui-styling/
│       ├── LICENSE.txt
│       ├── SKILL.md
│       ├── canvas-fonts/
│       ├── references/
│       └── scripts/
└── install.sh                       # Local and remote installer
```

## Adding or updating a skill

1. Create or edit the skill under `skills/<skill-name>/`.
2. Ensure its main file is named `SKILL.md` and contains valid frontmatter:

   ```md
   ---
   name: skill-name
   description: Explain what the skill does and when an agent should use it.
   ---
   ```

3. The directory name must match `name` and use lowercase letters, numbers, and hyphens.
4. Document the skill in `docs/<skill-name>/README.md` and link it from the table under [Available skills](#available-skills).

The root `skills/` directory is the single source of truth. The installer copies from it directly into each selected agent's skills directory. The `docs/` directory is documentation only and is never installed.

## Security

Skills contain instructions that may direct an agent to read files, execute commands, or access external services. Audit every `SKILL.md`, script, and reference before installing skills from an untrusted source.
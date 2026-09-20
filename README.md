# AI Coding Skills

A collection of portable [Agent Skills](https://agentskills.io/) for AI coding agents. Each skill contains a `SKILL.md` file and optional supporting resources that agents load only when relevant.

## Supported agents

| Target | Project directory | `--agent` value |
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
  | sh -s -- --agent claude /path/to/project
```

Install one skill for one agent:

```sh
curl -fsSL https://raw.githubusercontent.com/masb0ymas/ai-coding-skills/main/install.sh \
  | sh -s -- --agent claude --skill authula /path/to/project
```

Arguments passed to a piped shell must come after `sh -s --`.

> Review remote scripts before piping them into a shell. You can download the installer first, inspect it, and then run it:
>
> ```sh
> curl -fsSLO https://raw.githubusercontent.com/masb0ymas/ai-coding-skills/main/install.sh
> less install.sh
> sh install.sh --agent claude --skill authula /path/to/project
> ```

Remote installation requires `curl` or `wget`, plus `tar`.

### Install from a local clone

Clone or download this repository, then run the installer from the repository root.

Install all skills for all agents:

```sh
./install.sh /path/to/project
```

Select one agent with `--agent`:

```sh
./install.sh --agent claude /path/to/project
./install.sh --agent agents /path/to/project
./install.sh --agent openclaude /path/to/project
./install.sh --agent zcode /path/to/project
```

Select one skill with `--skill`. Without `--agent`, the selected skill is installed for every supported agent:

```sh
./install.sh --skill authula /path/to/project
```

Select an agent and a skill together:

```sh
./install.sh --agent claude --skill authula /path/to/project
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
./install.sh --agent claude --skill authula "$HOME"
```

The same operation can be run remotely:

```sh
curl -fsSL https://raw.githubusercontent.com/masb0ymas/ai-coding-skills/main/install.sh \
  | sh -s -- --agent claude --skill authula "$HOME"
```

> Global locations depend on the agent. Claude Code uses `~/.claude/skills/`, while Zed and compatible Agent Skills clients can use `~/.agents/skills/`.

## Installer reference

```text
Usage: ./install.sh [--agent <agent>] [--skill <skill>] [--skip-graft-setup] [--graft-no-global] [destination]
```

| Option | Description | Default |
| --- | --- | --- |
| `--agent <agent>` | Target `all`, `agents`, `claude`, `openclaude`, or `zcode` | `all` |
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

### `authula`

Guidance for building authentication with [Authula](https://authula.dev/docs), a plugin-based authentication framework for Go.

Main topics include:

- library and standalone modes;
- email/password, OAuth2, sessions, JWT, TOTP, magic links, API keys, and other plugins;
- route mappings and endpoint protection;
- Docker, TOML, environment variables, CORS, and CSRF configuration;
- custom routes, hooks, service hooks, and custom plugins.

Example prompts after installation:

```text
Create a standalone Authula setup with PostgreSQL, email-password,
and sessions. Protect the /me endpoint and include config.toml and .env.example.
```

```text
Add Authula to this Go backend with GitHub OAuth and session authentication.
```

The agent will automatically discover and use `authula` when a request is related to Authula.

### `graft`

Repo-context workflow for repositories initialized with [Graft](https://github.com/nanonets/graft): a local, linked-markdown graph plus wiring/call graphs for finding code, understanding flows, tracing callers, and scoping edits with minimal token use.

Main topics include:

- `graft ask "<question>" --source` for location and understanding;
- `graft grep "<pattern>"` for exhaustive occurrences;
- `graft skeleton <file>` for a file’s API surface;
- `graft callers <symbol>` and `--depth N` for exact edges and blast radius;
- `graft map` for cold-start orientation;
- `graft build` / `graft check` for graph lifecycle and CI freshness.

Example prompts after installation:

```text
Run graft map, then explain how this repository is organized and where changes usually belong.
```

```text
Use graft to find where authentication errors are handled, then scope the smallest safe edit.
```

The agent will automatically discover and use `graft` whenever a task benefits from Graft’s context graph instead of grepping or reading source files directly.

### `postgres-best-practices`

Best practices and guidelines for working with PostgreSQL 14 through 18, with version-specific features tagged and environment-dependent examples annotated.

Main topics include:

- schema design, data types, normalization, and partitioning;
- indexing strategies, composite indexes, and partial/covering indexes;
- query optimization, `EXPLAIN ANALYZE`, bottlenecks, and planner tuning;
- query patterns: CTEs, window functions, lateral joins, UPSERT, JSONB, and anti-patterns;
- performance diagnostics, locks, `VACUUM`, and connection management;
- logical replication, hot standby, transaction isolation, backup/restore, security/roles, bulk loading, connection pooling, and major upgrades.

Example prompts after installation:

```text
Review this Postgres schema and suggest indexes for the most common query patterns.
```

```text
This query is slow under load. Use EXPLAIN ANALYZE and recommend the smallest safe optimization.
```

The agent will automatically discover and use `postgres-best-practices` when writing SQL, designing schemas, optimizing queries, or setting up Postgres.

### `typesafe-ai`

Guidance for building AI-powered software with [TypeSafe](https://docs.typesafe.ai/) System One models, including Jev. It turns natural language and application state into typed judgments and probabilities that code can combine.

Main topics include:

- `Choice`, `Noul`, and `Score` primitives for structured decisions;
- state design, instructions, criteria, and atomic question decomposition;
- routing, ranking, extraction, verification, reranking, and interaction patterns;
- speculative fan-out, confidence-gated routing, and composite scoring;
- live docs, SDK usage, cookbooks, and uncertainty handling.

Example prompts after installation:

```text
Design TypeSafe judgments for routing support tickets by intent, urgency, and required arguments.
```

```text
Replace this prompt-and-parse LLM step with a structured TypeSafe Choice plus confidence-based escalation.
```

The agent will automatically discover and use `typesafe-ai` when a feature needs programmable common sense or a prompt-and-parse step could become a structured decision.

## Repository structure

```text
.
├── skills/                          # Canonical source for every skill
│   ├── authula/
│   │   ├── SKILL.md
│   │   └── references/
│   ├── graft/
│   │   └── SKILL.md
│   ├── postgres-best-practices/
│   │   ├── SKILL.md
│   │   └── references/
│   └── typesafe-ai/
│       ├── LICENSE
│       └── SKILL.md
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

The root `skills/` directory is the single source of truth. The installer copies from it directly into each selected agent's skills directory.

## Security

Skills contain instructions that may direct an agent to read files, execute commands, or access external services. Audit every `SKILL.md`, script, and reference before installing skills from an untrusted source.

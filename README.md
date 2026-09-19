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
Usage: ./install.sh [--agent <agent>] [--skill <skill>] [destination]
```

| Option | Description | Default |
| --- | --- | --- |
| `--agent <agent>` | Target `all`, `agents`, `claude`, `openclaude`, or `zcode` | `all` |
| `--skill <skill>` | Install all skills or one skill by directory name | `all` |
| `-h`, `--help` | Show command help | — |
| `destination` | Project or home directory into which agent folders are installed | Current directory |

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

## Repository structure

```text
.
├── skills/                 # Canonical source for every skill
│   └── authula/
│       ├── SKILL.md
│       └── references/
├── agents/                 # Agent-specific entry points (no duplicated skills)
│   ├── .agents/skills -> ../../skills
│   ├── .claude/skills -> ../../skills
│   ├── .openclaude/skills -> ../../skills
│   └── .zcode/skills -> ../../skills
├── scripts/
│   └── sync-agents.sh      # Create or repair the agent symlinks
└── install.sh              # Local and remote installer
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
4. Changes are immediately visible through every `agents/<agent>/skills` symlink. No copying or synchronization is required after editing a skill.
5. If an agent symlink is missing or incorrect, recreate all links with:

   ```sh
   ./scripts/sync-agents.sh
   ```

6. Verify the links:

   ```sh
   readlink agents/.agents/skills
   readlink agents/.claude/skills
   readlink agents/.openclaude/skills
   readlink agents/.zcode/skills
   ```

   Each command should print `../../skills`.

The root `skills/` directory is the single source of truth. Never add or edit skills under `agents/`; those paths only link back to the canonical directory.

## Security

Skills contain instructions that may direct an agent to read files, execute commands, or access external services. Audit every `SKILL.md`, script, and reference before installing skills from an untrusted source.

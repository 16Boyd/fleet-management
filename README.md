# Shared Agent Skills and Agents

This repository is the source of truth for reusable skills and shared agent guidance across the fleet. Canonical skills live under `.agents/skills/`; canonical role agents live under `.agents/agents/`. The root `AGENTS.md` preserves the current Codex global guidance byte-for-byte. Its MCP routes, tools, and skills are Codex/T3-specific, so the exporter installs that file only for Codex. Role-agent bodies are designed to be harness-neutral.

## Use on a machine

Clone the central repository:

```sh
git clone https://github.com/jasonb194/fleet-management.git
```

After cloning, update the checkout and sync its skills into the machine's per-user harness folders:

```sh
git pull --ff-only
python scripts/sync_skills.py
python scripts/sync_agents.py
```

Use `python3` on macOS or Linux if `python` is not the Python 3 interpreter. On Windows, `py -3 scripts/sync_skills.py` is also suitable.

`sync_agents.py` requires Python 3.11 or newer because it uses the standard-library `tomllib` module.

The script reads skills from this checkout and copies them to:

- `$CODEX_HOME/skills`, defaulting to `~/.codex/skills`, for the T3 Code Codex provider
- `$CLAUDE_CONFIG_DIR/skills`, defaulting to `~/.claude/skills`
- `~/.agents/skills`, shared by current Codex CLI, Freebuff, and OpenCode

Run it from the repository checkout. It does not clone or pull the repository. `--dry-run` previews the destination paths; `--check` validates canonical skill names, frontmatter, and relative Markdown links without copying. `--home <path>` redirects all three destinations beneath a test home directory.

`sync_agents.py` exports the root `AGENTS.md` to the Codex user configuration directory and translates role agents for Codex, Claude Code, and OpenCode. By default it syncs all three harnesses. Use `--harness claude` (or `codex` or `opencode`) to sync just one harness; this checks and updates only that harness destination. For example, to install the agents in Claude Code, run `python scripts/sync_agents.py --harness claude`. It supports the same `--check`, `--dry-run`, and `--home <path>` options. `--check` validates the source files without writing or checking destinations; `--dry-run` previews selected outputs and checks for unsafe collisions.

## Sync behavior

The script replaces only destination skill folders whose names match skills in this repository. Unrelated skill folders are preserved. Each destination root has a `.repo-synced-skills.json` manifest listing the skill names this repository manages. If a managed skill is later removed from the repo, the script removes its destination copy only when the manifest identifies it as repo-managed. When names match, repository content takes precedence.

## Harness compatibility

| Harness | Skill discovery | Fleet sync destination |
| --- | --- | --- |
| T3 Code Codex provider | Uses the selected provider's native skills | `$CODEX_HOME/skills` |
| Codex CLI | Project and personal `.agents/skills` | `~/.agents/skills` |
| Claude Code | Project `.claude/skills`; personal `~/.claude/skills` | `$CLAUDE_CONFIG_DIR/skills` |
| Freebuff | Project `.agents/skills` or `.claude/skills`; local interactive CLI can load home skills | `~/.agents/skills` |
| OpenCode | Project and home `.agents/skills` or `.claude/skills` | `~/.agents/skills` |
| T3 Code Claude provider | Uses the selected provider's native skills | `$CLAUDE_CONFIG_DIR/skills` |
| T3 Code OpenCode provider | Uses the selected provider's native skills | `~/.agents/skills` |

The skill folders use the shared `SKILL.md` format. For remote or server contexts where Freebuff home skills are not loaded, use the repo's project-local `.agents/skills` directory. T3 Code's skill picker depends on its selected provider; refresh provider skills or restart the app if updates are not visible.

## Shared agents

Each `.agents/agents/<name>.md` file begins with a TOML metadata fence followed by the harness-neutral instruction body:

```toml
name = "reader-agent"
description = "Use proactively for reading files and analyzing documents."

[models]
codex = "gpt-6-luna"
# claude = "sonnet"       # optional, Claude-native model identifier
# opencode = "provider/model" # optional, OpenCode-native identifier

[reasoning]
codex = "low"
# claude = "high"         # optional native effort setting
# opencode = "variant"    # optional OpenCode-native variant
```

Model and reasoning values are target-native and opt-in per harness. The current agents specify their existing Codex model and reasoning effort; Claude and OpenCode fields are omitted until a target-native choice is configured. This avoids guessing provider IDs or silently replacing one harness's model with another harness's equivalent. The exporter maps Codex fields to TOML, Claude values to agent YAML front matter (`model` and `effort`), and OpenCode model/variant values to its native `model: provider/model#variant` form. An OpenCode variant requires an OpenCode model mapping.

The exporter writes shared guidance verbatim to Codex's `AGENTS.md`. Role agents go to each harness's `agents/` directory. `CODEX_HOME`, `CLAUDE_CONFIG_DIR`, and `OPENCODE_CONFIG_DIR` select destinations when set; `--home` redirects them beneath an isolated test home. Each harness config root has a `.repo-synced-agents.json` manifest. The script updates only listed outputs, refuses to overwrite unmanaged files, and removes stale outputs only when the manifest identifies them as managed by this repository.

Use `python scripts/sync_agents.py --check` to validate source metadata, `python scripts/sync_agents.py --dry-run --home /tmp/agent-sync-home` to preview all harnesses, and `python scripts/sync_agents.py --harness claude --home /tmp/agent-sync-home` to exercise only the Claude export in an isolated directory.

## Skill discovery references

- [Codex skills](https://developers.openai.com/codex/skills)
- [Claude Code skills](https://code.claude.com/docs/en/skills)
- [Freebuff skill guide](https://github.com/CodebuffAI/freebuff/blob/main/common/src/templates/initial-agents-dir/skills/README.md) and [loader](https://github.com/CodebuffAI/freebuff/blob/main/sdk/src/skills/load-skills.ts)
- [OpenCode skills](https://opencode.ai/docs/skills/)
- [T3 Code](https://github.com/pingdotgg/t3code)

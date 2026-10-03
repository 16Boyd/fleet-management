# Shared Agent Skills

This repository is the source of truth for reusable skills shared across the fleet. The canonical copies live under `.agents/skills/`. The first skills cover Proxmox SSH sessions and T3Code container setup.

## Use on a machine

Clone the central repository:

```sh
git clone https://github.com/jasonb194/fleet-management.git
```

After cloning, update the checkout and sync its skills into the machine's per-user harness folders:

```sh
git pull --ff-only
python scripts/sync_skills.py
```

Use `python3` on macOS or Linux if `python` is not the Python 3 interpreter. On Windows, `py -3 scripts/sync_skills.py` is also suitable.

The script reads skills from this checkout and copies them to:

- `$CODEX_HOME/skills`, defaulting to `~/.codex/skills`
- `$CLAUDE_CONFIG_DIR/skills`, defaulting to `~/.claude/skills`
- `~/.agents/skills`, shared by Freebuff and OpenCode

Run it from the repository checkout. It does not clone or pull the repository. `--dry-run` previews the destination paths; `--check` validates canonical skill names, frontmatter, and relative Markdown links without copying. `--home <path>` redirects all three destinations beneath a test home directory.

## Sync behavior

The script replaces only destination skill folders whose names match skills in this repository. Unrelated skill folders are preserved. Each destination root has a `.repo-synced-skills.json` manifest listing the skill names this repository manages. If a managed skill is later removed from the repo, the script removes its destination copy only when the manifest identifies it as repo-managed. When names match, repository content takes precedence.

## Harness compatibility

| Harness | Skill discovery | Fleet sync destination |
| --- | --- | --- |
| Codex | Project `.agents/skills`; personal `$CODEX_HOME/skills` | `$CODEX_HOME/skills` |
| Claude Code | Project `.claude/skills`; personal `~/.claude/skills` | `$CLAUDE_CONFIG_DIR/skills` |
| Freebuff | Project `.agents/skills` or `.claude/skills`; local interactive CLI can load home skills | `~/.agents/skills` |
| OpenCode | Project and home `.agents/skills` or `.claude/skills` | `~/.agents/skills` |
| T3 Code | Uses the selected provider's native skills; it has no separate global skill directory | Codex, Claude Code, or OpenCode destination above |

The skill folders use the shared `SKILL.md` format. For remote or server contexts where Freebuff home skills are not loaded, use the repo's project-local `.agents/skills` directory. T3 Code's skill picker depends on its selected provider; refresh provider skills or restart the app if updates are not visible. Freebuff is not listed as a T3 Code provider in the current T3 Code documentation.

## Skill discovery references

- [Codex skills](https://developers.openai.com/codex/skills)
- [Claude Code skills](https://docs.anthropic.com/en/docs/claude-code/slash-commands)
- [Freebuff skill guide](https://github.com/CodebuffAI/freebuff/blob/main/common/src/templates/initial-agents-dir/skills/README.md) and [loader](https://github.com/CodebuffAI/freebuff/blob/main/sdk/src/skills/load-skills.ts)
- [OpenCode skills](https://opencode.ai/docs/skills/)
- [T3 Code](https://github.com/pingdotgg/t3code)

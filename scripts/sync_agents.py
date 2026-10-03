#!/usr/bin/env python3
"""Export canonical shared guidance and agents to supported harness formats."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import tomllib
from dataclasses import dataclass
from pathlib import Path


REPOSITORY_ID = "fleet-management-agents"
MANIFEST_NAME = ".repo-synced-agents.json"
FRONTMATTER = re.compile(r"\A```toml\r?\n(.*?)\r?\n```(?:\r?\n|\Z)", re.DOTALL)
NAME_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
HARNESS_NAMES = {"codex", "claude", "opencode"}


class SyncError(Exception):
    """A source or destination could not be synced safely."""


@dataclass(frozen=True)
class Agent:
    name: str
    description: str
    models: dict[str, str]
    reasoning: dict[str, str]
    instructions: str


def read_agent(path: Path) -> Agent:
    if path.is_symlink():
        raise SyncError(f"Agent source is a symbolic link: {path}")
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise SyncError(f"Cannot read {path}: {error}") from error
    match = FRONTMATTER.match(content)
    if not match:
        raise SyncError(f"{path} must start with a TOML metadata fence")
    try:
        metadata = tomllib.loads(match.group(1))
    except tomllib.TOMLDecodeError as error:
        raise SyncError(f"Invalid TOML metadata in {path}: {error}") from error
    name = metadata.get("name")
    description = metadata.get("description")
    if not isinstance(name, str) or not NAME_PATTERN.fullmatch(name):
        raise SyncError(f"{path} must define a lowercase kebab-case name")
    if path.stem != name:
        raise SyncError(f"Agent name {name!r} does not match filename {path.name!r}")
    if not isinstance(description, str) or not description.strip():
        raise SyncError(f"{path} must define a non-empty description")
    if set(metadata) - {"name", "description", "models", "reasoning"}:
        raise SyncError(f"Unknown metadata fields in {path}")
    models = metadata.get("models", {})
    reasoning = metadata.get("reasoning", {})
    for label, values in (("models", models), ("reasoning", reasoning)):
        if not isinstance(values, dict) or set(values) - HARNESS_NAMES:
            raise SyncError(f"{path} has invalid [{label}] harness mapping")
        if any(not isinstance(value, str) or not value.strip() for value in values.values()):
            raise SyncError(f"{path} [{label}] values must be non-empty strings")
    if "opencode" in reasoning and "opencode" not in models:
        raise SyncError(f"{path} defines an OpenCode variant without an OpenCode model")
    if "opencode" in reasoning and "#" in models["opencode"]:
        raise SyncError(f"{path} must put the OpenCode variant in [reasoning], not the model value")
    instructions = content[match.end():].strip()
    if not instructions:
        raise SyncError(f"{path} has no agent instructions")
    return Agent(name, description.strip(), models, reasoning, instructions)


def discover_agents(root: Path) -> list[Agent]:
    if not root.is_dir():
        raise SyncError(f"Canonical agent directory not found: {root}")
    agents = [read_agent(path) for path in sorted(root.glob("*.md"))]
    if not agents:
        raise SyncError(f"No agent Markdown files found under {root}")
    names = [agent.name for agent in agents]
    if len(set(names)) != len(names):
        raise SyncError("Duplicate canonical agent names found")
    return agents


def toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def yaml_scalar(value: str) -> str:
    # JSON double-quoted strings are valid YAML scalars and preserve punctuation.
    return json.dumps(value, ensure_ascii=False)


def rendered_files(guidance: str, agents: list[Agent]) -> dict[str, dict[str, str]]:
    outputs: dict[str, dict[str, str]] = {name: {} for name in HARNESS_NAMES}
    outputs["codex"]["AGENTS.md"] = guidance
    for agent in agents:
        if "codex" in agent.models:
            codex_model = f"model = {toml_string(agent.models['codex'])}\n"
        else:
            codex_model = ""
        if "codex" in agent.reasoning:
            codex_effort = f"model_reasoning_effort = {toml_string(agent.reasoning['codex'])}\n"
        else:
            codex_effort = ""
        codex = (
            f"name = {toml_string(agent.name)}\n"
            f"description = {toml_string(agent.description)}\n"
            f"{codex_model}{codex_effort}"
            f"developer_instructions = {toml_string(agent.instructions)}\n"
        )
        outputs["codex"][f"agents/{agent.name}.toml"] = codex

        claude_fields = [f"name: {yaml_scalar(agent.name)}", f"description: {yaml_scalar(agent.description)}"]
        if "claude" in agent.models:
            claude_fields.append(f"model: {yaml_scalar(agent.models['claude'])}")
        if "claude" in agent.reasoning:
            claude_fields.append(f"effort: {yaml_scalar(agent.reasoning['claude'])}")
        outputs["claude"][f"agents/{agent.name}.md"] = "---\n" + "\n".join(claude_fields) + "\n---\n\n" + agent.instructions + "\n"

        opencode_fields = ["mode: subagent", f"description: {yaml_scalar(agent.description)}"]
        if "opencode" in agent.models:
            opencode_model = agent.models["opencode"]
            if "opencode" in agent.reasoning:
                opencode_model += f"#{agent.reasoning['opencode']}"
            opencode_fields.append(f"model: {yaml_scalar(opencode_model)}")
        outputs["opencode"][f"agents/{agent.name}.md"] = "---\n" + "\n".join(opencode_fields) + "\n---\n\n" + agent.instructions + "\n"
    return outputs


def validate_relative_path(value: object, manifest_path: Path) -> str:
    if not isinstance(value, str):
        raise SyncError(f"Invalid managed output path in {manifest_path}")
    path = Path(value)
    if path.is_absolute() or not path.parts or any(part in {".", ".."} for part in path.parts):
        raise SyncError(f"Unsafe managed output path {value!r} in {manifest_path}")
    if path.as_posix() != value:
        raise SyncError(f"Invalid managed output path {value!r} in {manifest_path}")
    return value


def load_manifest(base: Path) -> set[str]:
    path = base / MANIFEST_NAME
    if path.is_symlink():
        raise SyncError(f"Sync manifest is not a regular file: {path}")
    if not path.exists():
        return set()
    if not path.is_file():
        raise SyncError(f"Sync manifest is not a regular file: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise SyncError(f"Cannot read sync manifest {path}: {error}") from error
    if not isinstance(payload, dict) or payload.get("repository_id") != REPOSITORY_ID:
        raise SyncError(f"Sync manifest belongs to another repository: {path}")
    managed = payload.get("managed_files", [])
    if not isinstance(managed, list):
        raise SyncError(f"Invalid managed file list in {path}")
    return {validate_relative_path(item, path) for item in managed}


def ensure_safe_target(base: Path, relative: str) -> Path:
    target = base / relative
    current = base
    for part in Path(relative).parts:
        current = current / part
        if current.is_symlink():
            raise SyncError(f"Refusing to use a symbolic-link output path: {current}")
    if target.exists() and not target.is_file():
        raise SyncError(f"Agent output exists but is not a regular file: {target}")
    return target


def atomic_write(target: Path, content: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", prefix=".agent-sync-", suffix=".tmp", dir=target.parent, delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(content)
    try:
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            temporary.unlink()


def write_manifest(base: Path, managed: list[str]) -> None:
    path = base / MANIFEST_NAME
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise SyncError(f"Sync manifest is not a regular file: {path}")
    serialized = json.dumps({"format": 1, "repository_id": REPOSITORY_ID, "managed_files": managed}, indent=2) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") == serialized:
            return
    atomic_write(path, serialized)


def preflight_harness(base: Path, outputs: dict[str, str]) -> None:
    if base.is_symlink():
        raise SyncError(f"Harness config destination is a symbolic link: {base}")
    if base.exists() and not base.is_dir():
        raise SyncError(f"Harness config destination is not a regular directory: {base}")
    previous = load_manifest(base) if base.is_dir() else set()
    for relative in outputs:
        target = ensure_safe_target(base, relative)
        if target.exists() and relative not in previous:
            raise SyncError(f"Refusing to overwrite unmanaged file: {target}")
    for relative in previous - outputs.keys():
        ensure_safe_target(base, relative)


def sync_harness(label: str, base: Path, outputs: dict[str, str], dry_run: bool) -> None:
    if base.is_symlink():
        raise SyncError(f"Harness config destination is a symbolic link: {base}")
    if dry_run:
        preflight_harness(base, outputs)
        old = load_manifest(base) if base.is_dir() else set()
        print(f"{label}: would sync {len(outputs)} files to {base}")
        stale = sorted(old - outputs.keys())
        if stale:
            print(f"  would remove previously managed files: {', '.join(stale)}")
        return

    if base.exists() and (base.is_symlink() or not base.is_dir()):
        raise SyncError(f"Harness config destination is not a regular directory: {base}")
    base.mkdir(parents=True, exist_ok=True)
    previous = load_manifest(base)
    # Check every current and stale path before writing anything, so a collision
    # cannot leave a partially updated set of agent files.
    targets = {relative: ensure_safe_target(base, relative) for relative in outputs}
    stale = sorted(previous - outputs.keys())
    stale_targets = {relative: ensure_safe_target(base, relative) for relative in stale}
    for relative, target in targets.items():
        if target.exists() and relative not in previous:
            raise SyncError(f"Refusing to overwrite unmanaged file: {target}")
    updated = 0
    for relative, content in sorted(outputs.items()):
        target = targets[relative]
        if not target.exists() or target.read_text(encoding="utf-8") != content:
            atomic_write(target, content)
            updated += 1
    for relative in stale:
        target = stale_targets[relative]
        if target.exists():
            target.unlink()
    write_manifest(base, sorted(outputs))
    print(f"{label}: synced {len(outputs)} files to {base} ({updated} updated, {len(stale)} removed)")


def destinations(home_override: Path | None) -> dict[str, tuple[str, Path]]:
    if home_override is not None:
        home = home_override.expanduser().resolve()
        return {
            "codex": ("Codex", home / ".codex"),
            "claude": ("Claude Code", home / ".claude"),
            "opencode": ("OpenCode", home / ".config" / "opencode"),
        }
    home = Path.home()
    codex_home = Path(os.environ.get("CODEX_HOME", home / ".codex")).expanduser()
    claude_home = Path(os.environ.get("CLAUDE_CONFIG_DIR", home / ".claude")).expanduser()
    opencode_home = Path(os.environ.get("OPENCODE_CONFIG_DIR", home / ".config" / "opencode")).expanduser()
    return {"codex": ("Codex", codex_home), "claude": ("Claude Code", claude_home), "opencode": ("OpenCode", opencode_home)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="validate canonical guidance and agent sources without writing")
    mode.add_argument("--dry-run", action="store_true", help="preview harness outputs without writing")
    parser.add_argument("--home", type=Path, help="redirect all harness destinations beneath this home directory")
    arguments = parser.parse_args()
    repository_root = Path(__file__).resolve().parents[1]
    try:
        guidance_path = repository_root / "AGENTS.md"
        if guidance_path.is_symlink() or not guidance_path.is_file():
            raise SyncError(f"Canonical shared guidance not found: {guidance_path}")
        guidance = guidance_path.read_text(encoding="utf-8")
        if not guidance.strip():
            raise SyncError(f"Canonical shared guidance is empty: {guidance_path}")
        agents = discover_agents(repository_root / ".agents" / "agents")
        outputs = rendered_files(guidance, agents)
        if arguments.check:
            print(f"Validated shared guidance and {len(agents)} agents: {', '.join(agent.name for agent in agents)}")
            return 0
        targets = destinations(arguments.home)
        if not arguments.dry_run:
            for key, (_, base) in targets.items():
                preflight_harness(base, outputs[key])
        for key, (label, base) in targets.items():
            sync_harness(label, base, outputs[key], arguments.dry_run)
    except (SyncError, OSError, UnicodeError) as error:
        print(f"sync_agents: error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

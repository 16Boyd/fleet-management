#!/usr/bin/env python3
"""Sync this repository's skills into supported user-level harness folders."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import unquote, urlparse


REPOSITORY_ID = "fleet-management-skills"
MANIFEST_NAME = ".repo-synced-skills.json"
NAME_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
FRONTMATTER_PATTERN = re.compile(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|\Z)", re.DOTALL)
LINK_PATTERN = re.compile(r"\]\(([^)]+)\)")


class SyncError(Exception):
    """A source or destination could not be synced safely."""


def is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_no_symlinks(directory: Path) -> None:
    for path in directory.rglob("*"):
        if path.is_symlink():
            raise SyncError(f"Skill tree contains a symbolic link: {path}")


def tree_digest(directory: Path) -> str:
    ensure_no_symlinks(directory)
    digest = hashlib.sha256()
    for path in sorted(p for p in directory.rglob("*") if p.is_file()):
        relative = path.relative_to(directory).as_posix().encode("utf-8")
        digest.update(relative)
        digest.update(b"\0")
        digest.update(bytes.fromhex(sha256_file(path)))
    return digest.hexdigest()


def parse_skill_name(skill_file: Path) -> str:
    try:
        content = skill_file.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise SyncError(f"Cannot read {skill_file}: {error}") from error

    match = FRONTMATTER_PATTERN.match(content)
    if not match:
        raise SyncError(f"{skill_file} must start with YAML frontmatter between --- lines")

    frontmatter = match.group(1)
    name_match = re.search(r"^name\s*:\s*(.*?)\s*$", frontmatter, re.MULTILINE)
    description_match = re.search(r"^description\s*:\s*(.*?)\s*$", frontmatter, re.MULTILINE)
    if not name_match or not description_match:
        raise SyncError(f"{skill_file} frontmatter must include name and description")

    name = name_match.group(1).strip().strip("\"'")
    description = description_match.group(1).strip().strip("\"'")
    folder_name = skill_file.parent.name
    if not NAME_PATTERN.fullmatch(name):
        raise SyncError(f"Skill name {name!r} in {skill_file} is not lowercase kebab-case")
    if name != folder_name:
        raise SyncError(f"Skill name {name!r} does not match folder {folder_name!r}")
    if not description:
        raise SyncError(f"{skill_file} has an empty description")
    return name


def local_markdown_links(markdown: str) -> list[str]:
    without_fences = re.sub(r"```.*?```", "", markdown, flags=re.DOTALL)
    targets: list[str] = []
    for match in LINK_PATTERN.finditer(without_fences):
        raw = match.group(1).strip()
        if raw.startswith("<") and ">" in raw:
            raw = raw[1 : raw.index(">")]
        else:
            raw = raw.split(maxsplit=1)[0]
        parsed = urlparse(raw)
        if parsed.scheme or parsed.netloc or not parsed.path:
            continue
        if parsed.path.startswith("/"):
            continue
        if unquote(parsed.path).lower().endswith((".md", ".markdown")):
            targets.append(unquote(parsed.path))
    return targets


def validate_skill_links(skill_root: Path, skills_root: Path) -> None:
    for markdown_file in skill_root.rglob("*.md"):
        if markdown_file.is_symlink():
            raise SyncError(f"Skill source contains a symbolic link: {markdown_file}")
        try:
            content = markdown_file.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            raise SyncError(f"Cannot read {markdown_file}: {error}") from error
        for target in local_markdown_links(content):
            resolved = (markdown_file.parent / target).resolve()
            if not is_within(resolved, skills_root):
                raise SyncError(f"Local link escapes the skills tree: {markdown_file} -> {target}")
            if not resolved.is_file():
                raise SyncError(f"Broken local Markdown link: {markdown_file} -> {target}")


def discover_skills(skills_root: Path) -> list[tuple[str, Path, str]]:
    if not skills_root.is_dir():
        raise SyncError(f"Canonical skills directory not found: {skills_root}")

    found: list[tuple[str, Path, str]] = []
    for directory in sorted(skills_root.iterdir(), key=lambda path: path.name.casefold()):
        if directory.is_symlink():
            raise SyncError(f"Canonical skills directory contains a symbolic link: {directory}")
        if not directory.is_dir():
            continue
        for source_path in directory.rglob("*"):
            if source_path.is_symlink():
                raise SyncError(f"Skill source contains a symbolic link: {source_path}")
        skill_file = directory / "SKILL.md"
        if not skill_file.is_file():
            continue
        name = parse_skill_name(skill_file)
        validate_skill_links(directory, skills_root)
        found.append((name, directory, tree_digest(directory)))

    if not found:
        raise SyncError(f"No SKILL.md files found under {skills_root}")
    if len({name for name, _, _ in found}) != len(found):
        raise SyncError(f"Duplicate skill names found under {skills_root}")
    return found


def current_revision(repository_root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(repository_root), "rev-parse", "--verify", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def destinations(home_override: Path | None) -> list[tuple[str, Path]]:
    if home_override is not None:
        home = home_override.expanduser().resolve()
        return [
            ("T3 Code Codex provider", home / ".codex" / "skills"),
            ("Claude Code and T3 Code Claude provider", home / ".claude" / "skills"),
            ("Codex CLI, Freebuff, OpenCode, and T3 Code OpenCode provider", home / ".agents" / "skills"),
        ]

    home = Path.home()
    codex_home_value = os.environ.get("CODEX_HOME")
    claude_home_value = os.environ.get("CLAUDE_CONFIG_DIR")
    codex_home = Path(codex_home_value).expanduser() if codex_home_value else home / ".codex"
    claude_home = Path(claude_home_value).expanduser() if claude_home_value else home / ".claude"
    return [
        ("T3 Code Codex provider", codex_home / "skills"),
        ("Claude Code and T3 Code Claude provider", claude_home / "skills"),
        ("Codex CLI, Freebuff, OpenCode, and T3 Code OpenCode provider", home / ".agents" / "skills"),
    ]


def load_manifest(target_root: Path) -> set[str]:
    manifest_path = target_root / MANIFEST_NAME
    if not manifest_path.exists():
        return set()
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise SyncError(f"Sync manifest is not a regular file: {manifest_path}")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise SyncError(f"Cannot read sync manifest {manifest_path}: {error}") from error
    if not isinstance(manifest, dict):
        raise SyncError(f"Invalid sync manifest object in {manifest_path}")
    if manifest.get("repository_id") != REPOSITORY_ID:
        raise SyncError(
            f"Sync manifest belongs to another repository: {manifest_path}"
        )
    managed = manifest.get("managed_skills", [])
    if not isinstance(managed, list) or any(
        not isinstance(name, str) or not NAME_PATTERN.fullmatch(name) for name in managed
    ):
        raise SyncError(f"Invalid managed skill list in {manifest_path}")
    return set(managed)


def replace_skill(source: Path, target: Path, target_root: Path) -> None:
    if target.is_symlink():
        raise SyncError(f"Refusing to replace a symbolic-link skill target: {target}")
    if target.exists() and not target.is_dir():
        raise SyncError(f"Skill target exists but is not a directory: {target}")

    with tempfile.TemporaryDirectory(prefix=".skill-sync-stage-", dir=target_root) as stage_name:
        stage_root = Path(stage_name)
        staged_skill = stage_root / source.name
        shutil.copytree(source, staged_skill)

        if target.exists() and tree_digest(target) == tree_digest(staged_skill):
            return

        backup_root = Path(tempfile.mkdtemp(prefix=".skill-sync-backup-", dir=target_root))
        backup_skill = backup_root / source.name
        moved_old = False
        try:
            if target.exists():
                os.replace(target, backup_skill)
                moved_old = True
            try:
                os.replace(staged_skill, target)
            except Exception:
                if moved_old:
                    os.replace(backup_skill, target)
                    moved_old = False
                raise
        finally:
            if backup_root.exists():
                shutil.rmtree(backup_root)


def write_manifest(target_root: Path, managed_names: list[str], revision: str | None) -> None:
    manifest_path = target_root / MANIFEST_NAME
    if manifest_path.is_symlink():
        raise SyncError(f"Refusing to replace a symbolic-link sync manifest: {manifest_path}")
    payload = {
        "format": 1,
        "repository_id": REPOSITORY_ID,
        "source_revision": revision,
        "managed_skills": managed_names,
    }
    serialized = json.dumps(payload, indent=2) + "\n"
    if manifest_path.exists():
        if manifest_path.is_symlink() or not manifest_path.is_file():
            raise SyncError(f"Sync manifest is not a regular file: {manifest_path}")
        try:
            if manifest_path.read_text(encoding="utf-8") == serialized:
                return
        except (OSError, UnicodeError) as error:
            raise SyncError(f"Cannot read sync manifest {manifest_path}: {error}") from error
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", newline="\n", prefix=".skill-sync-manifest-",
        suffix=".tmp", dir=target_root, delete=False
    ) as stream:
        temporary_path = Path(stream.name)
        stream.write(serialized)
    try:
        os.replace(temporary_path, manifest_path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def sync_target(
    label: str,
    target_root: Path,
    skills: list[tuple[str, Path, str]],
    revision: str | None,
    dry_run: bool,
) -> None:
    names = [name for name, _, _ in skills]
    if dry_run:
        stale = sorted(load_manifest(target_root) - set(names)) if target_root.is_dir() else []
        print(f"{label}: would sync {len(names)} skills to {target_root}")
        if stale:
            print(f"  would remove previously managed skills: {', '.join(stale)}")
        return

    target_root.mkdir(parents=True, exist_ok=True)
    if target_root.is_symlink() or not target_root.is_dir():
        raise SyncError(f"Skill destination is not a regular directory: {target_root}")
    previously_managed = load_manifest(target_root)

    updated = 0
    for name, source, source_digest in skills:
        target = target_root / name
        if target.is_symlink():
            raise SyncError(f"Refusing to replace a symbolic-link skill target: {target}")
        if target.exists() and target.is_dir() and tree_digest(target) == source_digest:
            continue
        replace_skill(source, target, target_root)
        updated += 1

    stale = sorted(previously_managed - set(names))
    for name in stale:
        target = target_root / name
        if target.is_symlink():
            raise SyncError(f"Refusing to remove a symbolic-link stale skill: {target}")
        if target.exists():
            if not target.is_dir():
                raise SyncError(f"Previously managed skill is not a directory: {target}")
            ensure_no_symlinks(target)
            shutil.rmtree(target)

    write_manifest(target_root, names, revision)
    removed = len(stale)
    print(f"{label}: synced {len(names)} skills to {target_root} ({updated} updated, {removed} removed)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="validate repository skills without copying")
    mode.add_argument("--dry-run", action="store_true", help="show target directories without writing")
    parser.add_argument(
        "--home", type=Path,
        help="use this temporary home for all harness targets (useful for validation)",
    )
    arguments = parser.parse_args()

    repository_root = Path(__file__).resolve().parents[1]
    skills_root = repository_root / ".agents" / "skills"
    try:
        skills = discover_skills(skills_root)
        names = [name for name, _, _ in skills]
        if arguments.check:
            print(f"Validated {len(names)} skills: {', '.join(names)}")
            return 0

        revision = current_revision(repository_root)
        targets = destinations(arguments.home)
        if arguments.dry_run:
            print(f"Validated {len(names)} skills: {', '.join(names)}")
        for label, target_root in targets:
            sync_target(label, target_root, skills, revision, arguments.dry_run)
    except SyncError as error:
        print(f"sync_skills: error: {error}", file=sys.stderr)
        return 1
    except OSError as error:
        print(f"sync_skills: filesystem error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

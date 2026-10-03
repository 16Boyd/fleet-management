---
name: tag-default-branch
description: Manually classify changes on the current repository's remote default branch and propose its next stable semantic version tag.
---

# Tag the Default Branch

Use this skill only when the user explicitly invokes it. Review changes on the current repository's remote default branch, classify the release, and propose a stable `MAJOR.MINOR.PATCH` tag. Do not create or push a tag until the user confirms the exact proposed tag.

## Inspect the release range

1. Confirm the repository root and its `origin` remote. Discover the remote default branch from `origin` (for example, `git ls-remote --symref origin HEAD`); do not assume it is `main` or `master`. If there is no unambiguous remote default branch or `origin` is unavailable, stop and explain.
2. Fetch the default branch and tags from `origin`, then inspect the fetched default-branch tip without checking it out. Do not change branches, the index, or the default branch worktree.
3. Find the most recent reachable stable semantic-version tag on that branch. Follow a consistent existing tag prefix convention (`v1.2.3` or `1.2.3`) when one exists. Exclude prerelease/build tags from the stable baseline. If no reachable stable semver tag exists, stop and ask the user for the intended starting version. If multiple tags create an ambiguous baseline or conflicting next tag, stop and explain.
4. Review the complete diff from that baseline to the fetched default-branch tip, plus the intervening commit history. Inspect relevant files as needed; commit subjects alone are not enough to establish compatibility. If the tip equals the baseline, report that there are no changes to release and do not propose a tag.

## Choose the version increment

Choose exactly one increment based on the cumulative changes since the baseline:

- **Major:** only for a confirmed breaking/incompatible change or a major overhaul. A large feature or ordinary refactor alone does not qualify. Explain the concrete break or overhaul.
- **Minor:** for backward-compatible, additive user-facing functionality.
- **Patch:** for bug fixes, documentation, maintenance, and compatible refinements.

When the evidence does not support a confident classification, or a possible breaking change/overhaul cannot be resolved from the repository, stop and ask the user rather than guessing. Use the highest applicable increment across the entire release range. Calculate the next version from the latest stable baseline and preserve its established prefix convention.

## Confirm and publish

Before changing refs, report the baseline tag and commit, remote default branch and fetched tip SHA, proposed tag and increment, and concise evidence for the classification. Ask the user to confirm that exact tag. Do not treat invocation of the skill as confirmation to publish.

After confirmation, verify that the exact tag name is absent both locally and on `origin`. Create an annotated tag pointing directly to the fetched default-branch tip SHA, with a concise release message. Push only that tag to `origin` (for example, `git push origin refs/tags/v1.2.3`). Never push a branch, force-update, move, or delete a tag. If the tag appeared or the remote tip changed before publishing, stop and re-evaluate against the updated state. Verify the pushed tag resolves to the intended SHA and report the result. If creation or push fails, report the actual state and do not attempt destructive recovery.

This workflow is manual only: do not install hooks, configure automation, schedule runs, or tag a different repository. Never tag the current feature branch just because it is checked out.

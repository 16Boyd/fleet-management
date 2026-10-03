---
name: proxmox-t3code-container
description: Provision a Debian LXC over SSH on Proxmox as a headless T3Code development host with the requested developer CLIs. Use only when the user wants this Proxmox container workflow.
---

# Proxmox T3Code Container

Use this workflow only for the requested Debian LXC developer host. Authoring this skill does not authorize a live deployment. Each run must obtain the approvals below before changing Proxmox or the container.

## Preflight and target approval

1. Before every Proxmox SSH connection, read and follow the sibling [proxmox-ssh-session skill](../proxmox-ssh-session/SKILL.md) from the same synced skills root. It is the single source of truth for SSH defaults, identity selection, effective-config checks, host-key handling, and local passphrase entry. If it cannot be read, stop before connecting. After it establishes access, continue this skill's Proxmox-specific read-only preflight. SSH access alone authorizes no remote mutation; keep the approval gates below.
2. Connect read-only first. Confirm the intended node, identity, and required Proxmox permissions. Use cluster resource data or inspect every node to find a free CTID: `pct list` on one node is not enough because CTIDs are cluster-wide. Choose a free ID in **300–399** and suggest `t3code-dev-<ctid>` as its lowercase hostname. Check the hostname against cluster resources and available name resolution; explain any check that cannot be made.
3. Verify the target node has `vmbr1`; `local-lvm` is active and supports `rootdir`; an active storage supports `vztmpl`; and the node and storage have capacity for 8 CPU cores, 16384 MB RAM, and a 40 GB disk. Use current [Proxmox `pct` documentation](https://pve.proxmox.com/pve-docs/pct.1.html), [storage documentation](https://pve.proxmox.com/pve-docs/pvesm.1.html), and [admin guide](https://pve.proxmox.com/pve-docs/pve-admin-guide.html) for command semantics. Stop on missing resources, conflicts, unclear permissions, or failed SSH/authentication.
4. Ask the user to approve the specific free CTID and suggested hostname, or provide replacements. Revalidate any replacement. Hostnames must be valid Debian hostnames (lowercase letters/digits/hyphens, no leading or trailing hyphen, at most 63 characters) and include `t3code`.

Before creation, consult the current [Community Scripts Debian page](https://community-scripts.org/scripts/debian), [unattended deployment guide](https://community-scripts.org/docs/guides/unattended_deployments), [technical reference](https://community-scripts.org/docs/technical_reference), and [helper source](https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/ct/debian.sh). This is third-party code that runs with Proxmox host privileges; it is not supported by Proxmox. Inspect the helper and its executable download chain locally before any PVE file write. Resolve and fetch a commit-pinned upstream copy when possible; otherwise keep the current reviewed bytes in a private local temporary directory. Inspect every mutable code dependency the helper executes or downloads; pin it to immutable bytes and hash it too. If any executed remote code cannot be identified and held to the reviewed bytes, stop. Record the resolved upstream commit (if available) and SHA-256 for the helper and dependencies. Define `reviewed_helper_file` as the private root-owned temporary path on the PVE host that will be created after approval. Clean up local staged copies if approval is declined or work stops, and clean up PVE copies through a trap.

Verify that the exact reviewed helper supports `mode=generated` and every requested variable, including `var_ctid`. Determine what `var_pw` means and how it is consumed. Prefer a verified stdin, file-descriptor, or private-file interface that does not propagate the secret in process environments. Never infer the behavior of an unset or empty password. If the helper only accepts `var_pw` through the environment, tell the user that the secret will be inherited by helper child processes and may be inspected by root processes on the PVE host during execution. Proceed only after the final approval explicitly consents to that exposure. If the input cannot be kept out of captured TTY input/output and logs, stop.

## Final approval and creation

Define `approved_ctid` as the free 300–399 CTID the user approved, and `approved_hostname` as the suggested/edited valid hostname containing `t3code` that the user approved. Show the exact target node, both approved values, helper source and resolved commit (or mutable-branch caveat), helper and dependency SHA-256 hashes, and complete settings before execution. State that approval covers transferring these exact reviewed bytes, creating the private PVE temp files, and creating/starting the container. Include the verified meaning of `var_pw` and where it will be entered. If `var_pw` must travel through the environment, include the process-inheritance/root-inspection disclosure above in the same approval prompt and ask for explicit informed consent. Preserve these settings from the user's example:

- `var_cpu=8`, `var_ram=16384`, `var_disk=40`
- approved `var_ctid` and `var_hostname`
- `var_brg=vmbr1`, `var_ssh=yes`, `var_protection=yes`
- `var_ipv6_method=none`, `var_container_storage=local-lvm`

Never reuse or repeat the example password. Only after the user approves the exact helper bytes/settings and, where applicable, explicitly consents to environment exposure, enter a fresh password through a non-echoing secure interactive terminal on the PVE host. Do not enter it in chat or a recorded terminal. Keep shell tracing off; do not store or echo it; use the least-exposing verified input channel and clear it immediately after execution. If a secure interactive channel is unavailable, stop.

After approval, create a private root-owned PVE temp directory under `umask 077` using race-safe `mktemp`, mode 700, and no symlink traversal. Transfer the local reviewed helper/dependency copies into it, set restrictive file modes, define `reviewed_helper_file` as the helper path there, verify every SHA-256 against the approved values, and recheck immediately before execution. Arrange trap-based cleanup on success or failure. If the code supports a verified stdin/FD/private-file secret interface, use it. If it only accepts `var_pw` in its environment and the user has consented, read the secret without echo into a short-lived `var_pw` shell variable on the PVE host and use the template below; the environment value is not hidden from root-level process inspection:

```bash
mode=generated \
var_cpu='8' \
var_ram='16384' \
var_disk='40' \
var_ctid="$approved_ctid" \
var_hostname="$approved_hostname" \
var_brg='vmbr1' \
var_ssh='yes' \
var_pw="$var_pw" \
var_protection='yes' \
var_ipv6_method='none' \
var_container_storage='local-lvm' \
bash "$reviewed_helper_file"
```

Substitute only the already approved and validated CTID/hostname and the path to the reviewed temporary helper copy. Never substitute a password literal. Recheck the helper/dependency hashes immediately before execution, then run this same reviewed copy on the PVE host.

Run the reviewed helper with the approved values. Confirm the created CTID and hostname match, then check `pct status` and `pct config`. If stopped, start it under the approval just obtained. Poll every 10 seconds for at most 10 minutes for both `pct status` to report `running` and a harmless `pct exec <approved_ctid> -- test -f /etc/os-release` check to succeed. On timeout, leave the CT intact and report the timeout. If creation is interrupted or the resulting CT does not match, leave it intact and report what happened; never overwrite, delete, or automatically recreate it.

## Install and verify

Once the intended container is running, use `pct exec` (it works without a guest IP) for read-only checks of Debian release and architecture. Read [references/software-sources.md](references/software-sources.md), check current official docs, and prepare all installer copies and version/integrity details locally before changing the CT. Do not create the `t3code` account, run apt, transfer files into the CT, or execute installers until the install approval below.

For each vendor shell installer, fetch the exact bytes into a private local temporary directory, verify an official signature/checksum when published, inspect the script and its executable download chain, and compute/display SHA-256. If no vendor integrity metadata exists, state that a hash identifies the bytes but does not authenticate them; get explicit approval for those exact bytes before execution. Pin/hash mutable executable dependencies too. Stop if a script would fetch unreviewed code after approval. Resolve the exact npm package versions and registry `dist.integrity` values. NPM verifies SRI for fetched package tarballs; use the documented `npm install -g <package>@<exact-version>` form only as `t3code`. If the transitive dependency tree cannot be pinned before install, disclose that resolution and lifecycle scripts may select/execute additional registry payloads; get explicit consent or stop. Report the exact requested-package versions and available integrity metadata in one consolidated post-CT install approval.

That approval must cover creating the unprivileged `t3code` account, installing the exact Debian package versions from verified repository metadata, transferring the reviewed installer files into a private user-owned temp directory in the CT, and running the reviewed installers and npm commands. Include hashes, signatures/checksum results, the exact NVM release, Node LTS version/checksum, T3Code and Claude Code artifact versions/hashes, exact npm package versions/integrity, and any unverified-authenticity or transitive-resolution caveat. After approval, install Python with `python3`, `python3-venv`, and `python3-pip`, plus only required HTTPS/tooling packages, as root. Install NVM, the pinned Node LTS release, PNPM, T3Code, Codex CLI, Claude Code CLI, OpenCode CLI, clasp, and Vercel CLI as `t3code`; do not install npm globals as root. Transfer each staged installer to a private account-owned directory, verify its approved hash, and execute that same copy. Do not run anything if bytes or metadata differ.

Use the documented headless T3Code service setup as this user. Recheck current official service docs and supported bind configuration; configure loopback before starting. If service installation auto-starts without a documented way to set loopback first, do not install/start the service. Measure the active socket with `ss -ltnp` and corroborate with service status. If loopback-only binding is unclear or cannot be verified, leave the service stopped and ask the user how to proceed. If making the service persistently available requires an additional host-level privilege such as enabling user lingering, explain the exact operation and get approval before that operation.

Do not sign in, launch an interactive CLI/TUI, configure provider/API credentials, deploy a Vercel project, expose a public listener, enable T3 Connect/Tailscale, or change network/firewall rules. Verify every requested executable using its documented version/help command in a fresh `t3code` login shell, and verify T3Code service status without logging in. If a CLI requires sign-in to finish setup, leave it installed and tell the user how to sign in later.

## Reruns and completion

On rerun, inspect the selected CTID and hostname first. Resume only the same matching container after showing the user what is already present and getting approval for any remaining mutations. If the ID belongs to a different guest or the hostname differs, stop; never overwrite or recreate it. Preserve a partially installed container after failures.

Report success only if every requested tool is installed and verified. Otherwise label the outcome **Partial completion** and list every missing or unverified tool and every failed/deferred step. Include the CTID, hostname, node, container status, `t3code` account, verified versions, and T3Code service status. Report a bind address only when measured from the active socket; otherwise say it was not verified. Mention remaining user sign-in steps without attempting them.

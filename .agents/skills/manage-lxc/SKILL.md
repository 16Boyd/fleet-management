---
name: manage-lxc
description: Use when the user asks to inspect or change the guest OS, software, files, services, or settings inside an existing Proxmox LXC container.
---

# Manage an LXC

Use this skill for work requested inside an existing Proxmox LXC. The user's request defines the allowed work; entering a container does not authorize unrelated changes.

## Enter the requested container

1. Before connecting, read and follow the sibling [`proxmox-ssh-session` skill](../proxmox-ssh-session/SKILL.md) from this same synced skills root. It is the source of truth for SSH defaults, identity and effective-configuration checks, host-key verification, and session handling. If it is unavailable or cannot be followed, stop before connecting.
2. Establish the verified SSH session using that skill. Confirm the selected CTID is an LXC owned by the node reached by the verified SSH session, using read-only cluster-wide resource data. Use a CTID the user supplied; if they supplied only a container name, resolve it only when it maps unambiguously to one CTID. A single node's local container list is insufficient to confirm cluster-wide identity. If the CTID or owning node cannot be confirmed, the name is ambiguous, or the target is on another node, stop and ask the user. For another node, request its verified endpoint/override, then follow the SSH skill again for that connection.
3. After confirming the target and that the verified SSH session is on its owning node, set `CTID` to the confirmed numeric ID. From the Proxmox host, enter the container in an interactive session:

   ```sh
   CTID=102
   pct enter "$CTID"
   ```

   Replace `102` with the confirmed CTID before running the command.

4. At the container shell, perform only the work the user requested, using guest commands inside that session. Keep any necessary Proxmox host inspection separate and read-only. Do not use `pct exec`, another container-entry method, or a non-interactive remote command as a substitute for `pct enter`.
5. Report what was completed and any errors or unfinished work, identifying the target CTID. If the SSH skill is unavailable, the container cannot be confirmed, or an interactive `pct enter` session cannot be maintained, stop and explain the blocker without attempting a bypass.

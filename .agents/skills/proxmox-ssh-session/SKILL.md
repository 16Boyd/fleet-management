---
name: proxmox-ssh-session
description: Open or use an SSH session to the user's Proxmox server for work they request on that host. Use when asked to connect to Proxmox, open its terminal, or run commands there.
---

# Proxmox SSH Session

Use this skill for SSH access to the user's Proxmox server. Each run authorizes only the connection and commands the user specifically requested; opening a shell grants no permission for other remote changes.

## Connection settings

Unless the user explicitly overrides a value for this run, use:

- Host: `192.168.90.2`
- Port: `22`
- Username: `root`
- Identity file: `$HOME/.ssh/proxmox_t3code` on Windows, macOS, or Linux. The private key must already be provisioned on that computer.

Require a local OpenSSH client with access to that identity file. If the current agent environment cannot access the user's local file, do not copy or upload the key; report that a local-client session is required. Never read, display, paste, copy, or upload private-key bytes. Do not ask for SSH passwords or passphrases in chat, argv, or environment. OpenSSH may prompt for a key passphrase through a trusted local TTY, or use an already-running agent. Do not run `ssh-add`, forward the agent, change ACLs, or fall back to another key. If the selected identity file is absent or OpenSSH rejects its permissions, stop and explain; do not weaken checks or change permissions.

## Verify and connect

Before each connection, check that the selected identity file exists and is usable without displaying its contents. With defaults, resolve `$HOME/.ssh/proxmox_t3code` in the current shell. Run OpenSSH's effective-configuration check using an isolated config and only the selected identity:

```sh
ssh -G -F none -o IdentityFile=none -p 22 -i "$HOME/.ssh/proxmox_t3code" -o IdentitiesOnly=yes -o ForwardAgent=no -o StrictHostKeyChecking=yes -o PreferredAuthentications=publickey root@192.168.90.2
```

For an explicit user override, substitute only the values the user changed. Confirm the effective output has the requested host, port, and username; the selected identity as the sole actual identity file (ignore the `none` sentinel); `identitiesonly yes`; `forwardagent no`; `stricthostkeychecking true`; public-key-only authentication; and the default user `known_hosts` path. If any setting differs or another actual identity is present, stop before connecting. `-F none` and `IdentityFile=none` prevent user/system SSH configuration or default keys from silently adding identities. See [OpenSSH `ssh(1)`](https://man.openbsd.org/ssh) and [`ssh_config(5)`](https://man.openbsd.org/ssh_config) for these options.

Then use the same isolated settings for the connection:

```sh
ssh -F none -o IdentityFile=none -p 22 -i "$HOME/.ssh/proxmox_t3code" -o IdentitiesOnly=yes -o ForwardAgent=no -o StrictHostKeyChecking=yes -o PreferredAuthentications=publickey root@192.168.90.2
```

When the user asks only to open a session, launch a local interactive SSH terminal with no remote command on startup. For a specific remote task, use this same connection method and run only the commands needed for that task, respecting its approval boundary.

Preserve the default user `known_hosts` file and `StrictHostKeyChecking=yes`. If a future connection has a missing or changed host pin, stop and have the user verify the fingerprint through a trusted path; never accept it automatically or disable checking.

Report whether the local identity/config check passed and whether the session opened. Do not show secret material or run unrequested remote commands.

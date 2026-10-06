# Server Auto Config

Ansible playbooks and roles to bootstrap Ubuntu servers: users, packages, Docker/Nginx/Certbot, GitLab Runner, SSH hardening, swap, Fail2ban, UFW, and a final reboot.

## Roles

There are **nine roles**. The playbook runs them in **two stages** (see `playbook/config.yml`): first through SSH configuration (with a handler flush so `sshd` restarts before the rest), then swap, Fail2ban, firewall, and reboot.

| Order | Role | What it does |
|------:|------|----------------|
| 1 | **user_config** | Creates the managed user and grants password-required sudo through a validated sudoers drop-in. |
| 2 | **manage_packages** | `apt` update/upgrade, then a script for unattended security updates and removal of a few legacy packages. |
| 3 | **install_deps** | Nginx, Certbot, Docker CE, Docker Compose plugin, and related packages. |
| 4 | **gitlab_runner** | Adds the GitLab Runner apt repo (keyring-based), installs Runner (with a binary fallback if apt fails), **registers once** if `/etc/gitlab-runner/config.toml` is missing, denies Runner sudo access, and removes privileged group membership. |
| 5 | **ssh_config** | Deploys `authorized_keys`, manages SSH policy and **SSH port** in `/etc/ssh/sshd_config.d/00-server-auto-config.conf`, and **restarts SSH** when config changes. |
| 6 | **swap_config** | 4G swap file (adjust size in the role tasks if needed); `fallocate` with `dd` fallback. |
| 7 | **fail2ban** | Installs Fail2ban; SSH jail port matches **`ssh_port`** from `group_vars`. |
| 8 | **firewall** | UFW: allow HTTP/HTTPS and your SSH port, then `ufw --force enable`. |
| 9 | **reboot** | Reboots the host (waits for it to come back). |

### Customization notes

- Edit **`roles/ssh_config/templates/00-server-auto-config.conf.j2`** for a different SSH policy. The `Port` directive comes from **`ssh_port`** in `playbook/group_vars/all.yml`. The old main-file content is retained as `roles/ssh_config/files/legacy_sshd_config` only to recognize installations managed by earlier versions.
- **Secrets:** use real values locally for `password`, `ssh_public_key`, and `gitlab_runner_registration_token`. Do not commit secrets; prefer [Ansible Vault](https://docs.ansible.com/ansible/latest/vault_guide/index.html) or a private vars file for production.

## Requirements

- **Ansible** on your control machine ([installation options](https://docs.ansible.com/ansible/latest/installation_guide/intro_installation.html)).
- **Target OS:** Ubuntu (roles use `apt` and Ubuntu-style service names, e.g. SSH service as `ssh`).

## Usage

### 1. Clone

```bash
git clone https://github.com/adel-bz/Server-Auto-Config.git
cd Server-Auto-Config
```

### 2. Configure variables

Edit **`playbook/group_vars/all.yml`** using the [variable reference](#variable-reference) below. Variables in `playbook/group_vars/` are loaded automatically when you run the playbook from the `playbook/` directory.

### 3. Configure inventory

Edit **`playbook/inventory.cnf`** and list your hosts under `[servers]`. You can use hostnames that match **`~/.ssh/config`**, or see [Ansible inventory docs](https://docs.ansible.com/ansible/latest/inventory_guide/intro_inventory.html).

### 4. Optional: trim roles

Edit **`playbook/config.yml`** and comment out any role you do not need.

### 5. Run the playbook

From the **`playbook/`** directory:

```bash
ansible-playbook -i inventory.cnf config.yml -K
```

`-K` prompts for the sudo password of the account Ansible connects as, which may
be different from the managed `user`. For unattended runs, supply
`ansible_become_password` through Ansible Vault. Do not put passwords on the
command line. SSH login remains key-only; the account password is used for sudo,
not SSH authentication.

### Sudo hardening and migration

The managed user retains full administrative sudo access, but must authenticate
with a password (normal sudo credential caching still applies). The role refuses
an empty or placeholder `password`, installs
`/etc/sudoers.d/99-server-auto-config-admin` as root-owned mode `0440`, and removes
the exact passwordless grant that older versions placed in `/etc/sudoers`.
Both the drop-in and combined sudoers configuration are checked with `visudo`.

GitLab Runner receives a sudo-deny drop-in and its legacy passwordless grant is
removed. It is also removed from the supplementary `sudo`, `admin`, and `docker`
groups, without replacing unrelated group memberships. A privileged primary
group causes the playbook to fail for manual correction. CI jobs that previously
used sudo or the host Docker socket will need an unprivileged workflow; this
change does not add deployment wrappers or configure rootless Docker.

Before applying to an existing server:

- Set a strong, private account password and confirm that the Ansible login
  account can still become root. Pass `-K` even if sudo is currently passwordless:
  later tasks may need the password once the old grant is removed. If Ansible
  changes its own login account's password, the become password must match the
  new value.
- Keep a separate tested administrative session or console available. Apply
  during a maintenance window after draining CI jobs.
- Review other sudo policies with `sudo -l -U <managed-user>` and
  `sudo -l -U gitlab-runner`. Sudo uses the last matching rule, so later external
  rules can override these drop-ins. The role does not delete unrelated policies.
  Confirm that the managed user needs a password after clearing its sudo cache
  with `sudo -k`, and that Runner cannot execute sudo commands.
- Group removal affects new sessions, not credentials held by existing
  processes. The full playbook's final reboot applies the group changes to all
  sessions; if that role is skipped, restart Runner and reconnect user sessions
  before considering the migration complete.

### SSH transition

After a successful run, if you changed the SSH port, the next connection from Ansible must use that port (configure inventory or `ansible_ssh_port` / SSH config accordingly). A failure to connect on port 22 can mean the new port is in effect.

The SSH role installs a drop-in under `/etc/ssh/sshd_config.d/`, validates both
the drop-in and combined configuration with `sshd -t`, checks the effective port
and key-only authentication settings with `sshd -T`, allows that port through
UFW when UFW is installed, and notifies a restart handler.
The main `/etc/ssh/sshd_config` must include `/etc/ssh/sshd_config.d/*.conf`, as
Ubuntu's default file does. On hosts where an earlier version of this role
replaced the main file, the role removes its old `Port` line once to avoid
listening on both the old and new ports. It leaves other main-file settings in
place; the managed drop-in is read first. An unrelated active `Port` directive
in the main file must be migrated manually before running this role. Before
making SSH changes, the role also rejects any active `Match` block in the main
file or recursively included files, including custom include paths. Ordinary
absolute/relative paths, double-quoted paths, and globs are supported; ambiguous
Include escaping or expansion syntax is rejected for manual review. This is a
deliberate fail-closed restriction, even for otherwise harmless `Match` blocks:
review and remove or migrate them manually rather than assuming the global
`sshd -T` output proves the policy for every connection. This preflight runs in
check mode too. Post-change effective-policy probes and assertions are skipped
in check mode because proposed configuration changes have not been applied.
On Ubuntu
24.04 with `ssh.socket` active, the handler reloads systemd to regenerate the socket
configuration and restarts both `ssh.socket` and `ssh.service`; otherwise it
restarts the SSH service. The playbook then resets the SSH connection and verifies
access on the configured port before starting the second play. Any external
firewall must also allow that port.

Before the first run, confirm that the SSH account Ansible uses can log in with
its private key. The managed SSH policy requires public-key authentication and
disables password and keyboard-interactive login. A key in the managed user's
`authorized_keys` does not by itself verify access for Ansible's initial SSH user.

If an older run changed `sshd_config` without restarting SSH, rerun the updated
playbook using the port the server still listens on for the initial connection.
Keep your local inventory and variable values when updating the development branch.

## Variable reference

All user-configurable variables are listed in **`playbook/group_vars/all.yml`**.
The values below are the shipped defaults or placeholders; replace placeholders
before running the roles that use them.

### User account

| Variable | Default / placeholder | Purpose |
|----------|-----------------------|---------|
| `user` | `"ubuntu"` | Linux account to create or manage (not `root` or `gitlab-runner`). Receives a Bash shell, sudo group membership, password-required sudo, and the configured SSH public key. Docker group membership is opt-in. This does not set Ansible's initial SSH login user; configure that in inventory or SSH config. |
| `password` | `"CHANGE_ME"` | Required non-placeholder password for the managed Linux account's sudo authentication. Supply the password itself; the role hashes it with SHA-512 before setting it. Store the value with Ansible Vault or in a private vars file. |

### SSH access

| Variable | Default / placeholder | Purpose |
|----------|-----------------------|---------|
| `ssh_port` | `"22"` | SSH listening port written to the managed drop-in. Also used by the Fail2ban SSH jail, the UFW SSH allow rule, and the connection settings for the second play. Use the server's current SSH port for the initial connection. |
| `ssh_public_key` | `"REPLACE_WITH_YOUR_SSH_PUBLIC_KEY"` | Single-line OpenSSH public key installed in the managed user's `authorized_keys` for SSH login. Supply a public key, never a private key. |

### GitLab Runner

| Variable | Default / placeholder | Purpose |
|----------|-----------------------|---------|
| `gitlab_runner_url` | `"https://gitlab.example.com"` | GitLab instance URL used when registering the runner. Replace it with the URL of your GitLab instance. |
| `gitlab_runner_registration_token` | `"REPLACE_WITH_GITLAB_RUNNER_TOKEN"` | Token passed to `gitlab-runner register --registration-token` when registering the runner. Store it with Ansible Vault or in a private vars file. |
| `gitlab_runner_executor` | `"shell"` | Executor passed during runner registration. The default `shell` executor runs CI jobs directly on the host; another executor may require additional configuration. |

Runner registration is skipped when `/etc/gitlab-runner/config.toml` already
exists, so changing the runner variables does not update an existing registration.

### Docker access and log rotation

| Variable | Default / placeholder | Purpose |
|----------|-----------------------|---------|
| `docker_add_user_to_group` | `false` | Whether the managed user gets Docker group access. By default, the role removes existing supplementary Docker membership. Set to `true` only if you accept root-equivalent access without a sudo password. Does not grant Docker access to GitLab Runner. |
| `docker_log_max_file` | `3` | Maximum number of log files retained per container by Docker's default `json-file` logging configuration. Use a positive integer; older files are removed as rotation exceeds this limit. |
| `docker_log_max_size` | `"10m"` | Maximum size of each Docker log file before rotation. Use a positive integer followed by `k`, `m`, or `g`, for example `"10m"` for 10 MB or `"1g"` for 1 GB. |

The [Docker group grants root-level privileges](https://docs.docker.com/engine/install/linux-postinstall/).
With the default opt-out, use password-authenticated sudo for Docker management.
Setting `docker_add_user_to_group: true` deliberately bypasses that boundary.

Docker uses the `json-file` logging driver with log rotation enabled by default.
Change these variables in **`playbook/group_vars/all.yml`** to adjust the limits:

```yaml
docker_log_max_file: 3
docker_log_max_size: "10m"
```

This keeps at most three log files per container, each up to 10 MB. The size
requires a unit suffix (`k`, `m`, or `g`). The role merges these settings into
`/etc/docker/daemon.json`, preserves unrelated daemon settings, validates the
configuration, and restarts Docker when it changes. As described in the
[Docker logging documentation](https://docs.docker.com/engine/logging/drivers/json-file/),
the new defaults apply to newly created containers; recreate existing containers
to use them. Container-specific logging options can override these defaults.

## Contributing

1. Fork the repository.
2. Create a branch: `git checkout -b feature-name`
3. Commit and push: `git commit -m "Describe your change"` then `git push origin feature-name`
4. Open a pull request.

Please keep commits focused and avoid committing secrets or real inventory hostnames.

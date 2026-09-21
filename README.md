# Server Auto Config

Ansible playbooks and roles to bootstrap Ubuntu servers: users, packages, Docker/Nginx/Certbot, GitLab Runner, SSH hardening, swap, Fail2ban, UFW, and a final reboot.

## Roles

There are **nine roles**. The playbook runs them in **two stages** (see `playbook/config.yml`): first through SSH configuration (with a handler flush so `sshd` restarts before the rest), then swap, Fail2ban, firewall, and reboot.

| Order | Role | What it does |
|------:|------|----------------|
| 1 | **user_config** | Creates the managed user, adds sudo access (passwordless sudo as configured in the role). |
| 2 | **manage_packages** | `apt` update/upgrade, then a script for unattended security updates and removal of a few legacy packages. |
| 3 | **install_deps** | Nginx, Certbot, Docker CE, Docker Compose plugin, and related packages. |
| 4 | **gitlab_runner** | Adds the GitLab Runner apt repo (keyring-based), installs Runner (with a binary fallback if apt fails), **registers once** if `/etc/gitlab-runner/config.toml` is missing, then sudo rules for `gitlab-runner` as in the role. |
| 5 | **ssh_config** | Deploys `authorized_keys`, copies `sshd_config`, sets **SSH port** from `ssh_port` in `group_vars`, **restarts the SSH service** when config changes. |
| 6 | **swap_config** | 4G swap file (adjust size in the role tasks if needed); `fallocate` with `dd` fallback. |
| 7 | **fail2ban** | Installs Fail2ban; SSH jail port matches **`ssh_port`** from `group_vars`. |
| 8 | **firewall** | UFW: allow HTTP/HTTPS and your SSH port, then `ufw --force enable`. |
| 9 | **reboot** | Reboots the host (waits for it to come back). |

### Customization notes

- Replace **`roles/ssh_config/files/sshd_config`** with your own file if you need different SSH policy; keep `Port` consistent with **`ssh_port`** in `playbook/group_vars/all.yml` (the role also forces the port line).
- **Secrets:** use real values locally for `password`, `ssh_public_key`, and `gitlab_runner_registration_token`. Do not commit secrets; prefer [Ansible Vault](https://docs.ansible.com/ansible/latest/vault_guide/index.html) or a private vars file for production.

> The banner image in the introduction may still point at assets from the older repo name on GitHub; clone URL below matches **Server-Auto-Config**.

https://github.com/adel-bz/Ansible-Server-Config/assets/45201934/46729180-8423-464c-b103-7bfbad9174b4

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
ansible-playbook -i inventory.cnf config.yml
```

If SSH or sudo needs a password interactively:

```bash
ansible-playbook -i inventory.cnf config.yml -kK
```

After a successful run, if you changed the SSH port, the next connection from Ansible must use that port (configure inventory or `ansible_ssh_port` / SSH config accordingly). A failure to connect on port 22 can mean the new port is in effect.

## Variable reference

All user-configurable variables are listed in **`playbook/group_vars/all.yml`**.
The values below are the shipped defaults or placeholders; replace placeholders
before running the roles that use them.

### User account

| Variable | Default / placeholder | Purpose |
|----------|-----------------------|---------|
| `user` | `"ubuntu"` | Linux account to create or manage. The roles give it a Bash shell, sudo group membership, passwordless sudo, Docker group membership, and the configured SSH public key. This does not set Ansible's initial SSH login user; configure that in inventory or SSH config. |
| `password` | `"CHANGE_ME"` | Password for the managed Linux account. Supply the password itself; the role hashes it with SHA-512 before setting it. Store the value with Ansible Vault or in a private vars file. |

### SSH access

| Variable | Default / placeholder | Purpose |
|----------|-----------------------|---------|
| `ssh_port` | `"22"` | SSH listening port configured on the server. Also used by the Fail2ban SSH jail, the UFW SSH allow rule, and the connection settings for the second play. Use the server's current SSH port for the initial connection. |
| `ssh_public_key` | `"REPLACE_WITH_YOUR_SSH_PUBLIC_KEY"` | Single-line OpenSSH public key installed in the managed user's `authorized_keys` for SSH login. Supply a public key, never a private key. |

### GitLab Runner

| Variable | Default / placeholder | Purpose |
|----------|-----------------------|---------|
| `gitlab_runner_url` | `"https://gitlab.example.com"` | GitLab instance URL used when registering the runner. Replace it with the URL of your GitLab instance. |
| `gitlab_runner_registration_token` | `"REPLACE_WITH_GITLAB_RUNNER_TOKEN"` | Token passed to `gitlab-runner register --registration-token` when registering the runner. Store it with Ansible Vault or in a private vars file. |
| `gitlab_runner_executor` | `"shell"` | Executor passed during runner registration. The default `shell` executor runs CI jobs directly on the host; another executor may require additional configuration. |

Runner registration is skipped when `/etc/gitlab-runner/config.toml` already
exists, so changing the runner variables does not update an existing registration.

### Docker log rotation

| Variable | Default / placeholder | Purpose |
|----------|-----------------------|---------|
| `docker_log_max_file` | `3` | Maximum number of log files retained per container by Docker's default `json-file` logging configuration. Use a positive integer; older files are removed as rotation exceeds this limit. |
| `docker_log_max_size` | `"10m"` | Maximum size of each Docker log file before rotation. Use a positive integer followed by `k`, `m`, or `g`, for example `"10m"` for 10 MB or `"1g"` for 1 GB. |

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

## Verifying the run

- **SSH port changed:** reconnect using the new port; “connection refused” on 22 alone may be expected.
- **No errors:** playbook finishes green for all tasks.

## Contributing

1. Fork the repository.
2. Create a branch: `git checkout -b feature-name`
3. Commit and push: `git commit -m "Describe your change"` then `git push origin feature-name`
4. Open a pull request.

Please keep commits focused and avoid committing secrets or real inventory hostnames.

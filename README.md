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

Edit **`playbook/group_vars/all.yml`** (e.g. `ssh_port`, `user`, `password`, `ssh_public_key`, GitLab URL and runner token). Variables in `playbook/group_vars/` are loaded automatically when you run the playbook from the `playbook/` directory.

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

## Verifying the run

- **SSH port changed:** reconnect using the new port; “connection refused” on 22 alone may be expected.
- **No errors:** playbook finishes green for all tasks.

Screenshots (historical):

![SSH port change / connection behavior](https://github.com/adel-bz/Ansible-Server-Config/assets/45201934/9a9ef4cc-5a39-4c47-9d58-a729da706942)

![Successful run](https://github.com/adel-bz/Ansible-Server-Config/assets/45201934/03e0c500-2a02-460c-a4b7-d200857ca954)

## Contributing

1. Fork the repository.
2. Create a branch: `git checkout -b feature-name`
3. Commit and push: `git commit -m "Describe your change"` then `git push origin feature-name`
4. Open a pull request.

Please keep commits focused and avoid committing secrets or real inventory hostnames.

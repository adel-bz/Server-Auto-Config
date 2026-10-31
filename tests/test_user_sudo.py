"""Render the real administrator sudo policy into isolated temporary files."""

import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile
import unittest

import yaml


REPO = Path(__file__).resolve().parents[1]
ROLE = REPO / 'roles/user_config'
VISUDO = shutil.which('visudo')


@unittest.skipUnless(VISUDO, 'visudo is required to validate rendered sudoers policies')
class UserSudoTests(unittest.TestCase):
    def run_policy(self, username='example-admin', check_mode=False):
        with tempfile.TemporaryDirectory(prefix='user-sudo-test-') as directory:
            root = Path(directory)
            policy = root / '99-server-auto-config-admin'
            sudoers = root / 'sudoers'
            sudoers.write_text(
                'root ALL=(ALL:ALL) ALL\n'
                '%sudo ALL=(ALL:ALL) ALL\n'
                f'{username} ALL=(ALL) NOPASSWD: ALL\n'
                f'#include {policy}\n'
            )
            sudoers.chmod(0o440)
            tasks = yaml.safe_load((ROLE / 'tasks/main.yml').read_text())
            selected = []
            for task in tasks:
                if 'template' in task:
                    task['template']['src'] = str(ROLE / 'templates' / task['template']['src'])
                    task['template']['dest'] = str(policy)
                    # Test the actual write and validation without requiring root.
                    task['template'].pop('owner')
                    task['template'].pop('group')
                elif 'lineinfile' in task:
                    task['lineinfile']['dest'] = str(sudoers)
                elif task.get('command') == 'visudo -c':
                    task['command'] = {'argv': [VISUDO, '-c', '-f', str(sudoers)]}
                elif task['name'] != 'Validate managed administrator name':
                    continue  # Never create an account or read the host's sudoers.
                task['become'] = False
                selected.append(task)
            playbook = root / 'playbook.yml'
            playbook.write_text(yaml.safe_dump([{
                'hosts': 'localhost', 'connection': 'local', 'gather_facts': False,
                'vars': {'user': username}, 'tasks': selected,
            }]))
            environment = dict(
                os.environ,
                ANSIBLE_LOCAL_TEMP=str(root / 'local-tmp'),
                ANSIBLE_REMOTE_TEMP=str(root / 'remote-tmp'),
                ANSIBLE_NOCOLOR='1',
                ANSIBLE_INVENTORY_ENABLED='host_list',
            )
            command = ['ansible-playbook', '-i', 'localhost,', str(playbook)]
            if check_mode:
                command.append('--check')
            result = subprocess.run(command, env=environment, capture_output=True, text=True)
            content = policy.read_text() if policy.exists() else None
            mode = stat.S_IMODE(policy.stat().st_mode) if policy.exists() else None
            return result, content, mode, sudoers.read_text()

    def test_managed_user_gets_passwordless_all_commands_after_group_policy(self):
        result, content, mode, sudoers = self.run_policy()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        rules = [line.strip() for line in content.splitlines()
                 if line.strip() and not line.lstrip().startswith('#')]
        self.assertEqual(rules, ['example-admin ALL=(ALL:ALL) NOPASSWD: ALL'])
        self.assertEqual(mode, 0o440)
        self.assertIn('%sudo ALL=(ALL:ALL) ALL', sudoers)
        self.assertNotIn('example-admin ALL=(ALL) NOPASSWD: ALL', sudoers)

    def test_check_mode_does_not_write_policy_or_remove_legacy_grant(self):
        result, content, _, sudoers = self.run_policy(check_mode=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIsNone(content)
        self.assertIn('example-admin ALL=(ALL) NOPASSWD: ALL', sudoers)

    def test_runner_cannot_receive_managed_administrator_policy(self):
        result, content, _, _ = self.run_policy(username='gitlab-runner')
        self.assertNotEqual(result.returncode, 0)
        self.assertIsNone(content)


if __name__ == '__main__':
    unittest.main()

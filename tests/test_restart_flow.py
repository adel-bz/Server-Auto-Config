"""Test deferred SSH activation and reboot acceptance without rebooting a host."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import yaml


REPO = Path(__file__).resolve().parents[1]


class RestartFlowTests(unittest.TestCase):
    def test_ssh_role_only_writes_and_validates_configuration(self):
        tasks = yaml.safe_load((REPO / 'roles/ssh_config/tasks/main.yml').read_text())
        self.assertFalse((REPO / 'roles/ssh_config/handlers/main.yml').exists())
        for task in tasks:
            self.assertNotIn('notify', task)
            for module in ['service', 'systemd', 'systemd_service', 'reboot',
                           'wait_for_connection', 'wait_for', 'meta']:
                self.assertNotIn(module, task)
                self.assertNotIn(f'ansible.builtin.{module}', task)
            command = task.get('command', '')
            if command:
                self.assertTrue(command.startswith('/usr/sbin/sshd -'), command)
        self.assertTrue(any(task.get('command') == '/usr/sbin/sshd -t -f /etc/ssh/sshd_config'
                            for task in tasks))
        self.assertTrue(any(task.get('command') == '/usr/sbin/sshd -T -f /etc/ssh/sshd_config'
                            for task in tasks))

    def test_playbook_keeps_connection_settings_and_reboots_last(self):
        plays = yaml.safe_load((REPO / 'playbook/config.yml').read_text())
        for play in plays:
            self.assertNotIn('post_tasks', play)
            self.assertNotIn('ansible_port', play.get('vars', {}))
            self.assertNotIn('ansible_user', play.get('vars', {}))
        self.assertEqual(plays[-1]['roles'][-1]['role'], '../roles/reboot')

    def test_reboot_role_flushes_handlers_before_scheduling(self):
        tasks = yaml.safe_load((REPO / 'roles/reboot/tasks/main.yml').read_text())
        self.assertEqual(len(tasks), 2)
        self.assertEqual(tasks[0]['ansible.builtin.meta'], 'flush_handlers')
        reboot = tasks[1]
        self.assertEqual(reboot['ansible.builtin.command']['argv'],
                         ['/sbin/shutdown', '-r', '+1', 'Reboot initiated by Ansible'])
        self.assertTrue(reboot['become'])
        self.assertTrue(reboot['changed_when'])
        self.assertEqual(reboot['when'], 'not ansible_check_mode')
        self.assertNotIn('ignore_unreachable', reboot)
        self.assertNotIn('ignore_errors', reboot)
        self.assertNotIn('failed_when', reboot)

    def run_reboot_role(self, return_code=0, check_mode=False):
        with tempfile.TemporaryDirectory(prefix='reboot-role-test-') as directory:
            root = Path(directory)
            marker = root / 'request.json'
            mock = root / 'mock_shutdown.py'
            mock.write_text(
                'import json, sys\nfrom pathlib import Path\n'
                f'Path({str(marker)!r}).write_text(json.dumps(sys.argv[1:]))\n'
                f'sys.exit({return_code})\n'
            )
            tasks = yaml.safe_load((REPO / 'roles/reboot/tasks/main.yml').read_text())
            task = tasks[-1]
            argv = task['ansible.builtin.command']['argv']
            # Substitute only the shutdown executable, never run a real reboot.
            task['ansible.builtin.command']['argv'] = [sys.executable, str(mock)] + argv[1:]
            task['become'] = False
            playbook = root / 'playbook.yml'
            playbook.write_text(yaml.safe_dump([{
                'hosts': 'localhost', 'connection': 'local', 'gather_facts': False,
                'tasks': tasks,
            }]))
            environment = dict(os.environ,
                               ANSIBLE_LOCAL_TEMP=str(root / 'local-tmp'),
                               ANSIBLE_REMOTE_TEMP=str(root / 'remote-tmp'),
                               ANSIBLE_NOCOLOR='1',
                               ANSIBLE_INVENTORY_ENABLED='host_list')
            command = ['ansible-playbook', '-i', 'localhost,', str(playbook)]
            if check_mode:
                command.append('--check')
            result = subprocess.run(command, env=environment, capture_output=True, text=True)
            request = json.loads(marker.read_text()) if marker.exists() else None
            return result, request

    def test_accepted_reboot_request_finishes_without_waiting(self):
        result, request = self.run_reboot_role()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(request, ['-r', '+1', 'Reboot initiated by Ansible'])
        self.assertIn('changed=1', result.stdout)
        self.assertIn('failed=0', result.stdout)

    def test_rejected_reboot_request_fails_instead_of_reporting_success(self):
        result, request = self.run_reboot_role(return_code=7)
        self.assertNotEqual(result.returncode, 0)
        self.assertIsNotNone(request)
        self.assertIn('failed=1', result.stdout)

    def test_check_mode_never_requests_a_reboot(self):
        result, request = self.run_reboot_role(check_mode=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIsNone(request)
        self.assertIn('skipped=1', result.stdout)

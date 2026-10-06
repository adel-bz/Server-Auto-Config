"""Read-only SSH regression tests; no SSH daemon is started.

Run with the Python environment containing Ansible and PyYAML:
    python -m unittest discover -s tests -v
"""

import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import yaml


REPO = Path(__file__).resolve().parents[1]
SCANNER = REPO / 'roles/ssh_config/files/reject_match_rules.py'
TASKS = REPO / 'roles/ssh_config/tasks/main.yml'
spec = importlib.util.spec_from_file_location('ssh_preflight', SCANNER)
preflight = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preflight)


class SSHPolicyTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='ssh-policy-test-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.main = self.write('sshd_config', '# Default configuration\n')

    def write(self, filename, content):
        path = self.root / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def check(self):
        preflight.reject_match_rules(self.main, include_root=self.root)

    def test_comments_and_global_policy_are_accepted(self):
        self.main.write_text('# Match User root\nPermitRootLogin no\n')
        self.check()

    def test_retained_root_override_is_rejected_without_modification(self):
        contents = 'Match User root\n PermitRootLogin prohibit-password\n'
        self.main.write_text(contents)
        with self.assertRaisesRegex(ValueError, 'sshd_config:1: retained Match'):
            self.check()
        self.assertEqual(self.main.read_text(), contents)

    def test_all_match_selectors_are_rejected(self):
        for selector in ['User root', 'Group admins', 'Address 192.0.2.0/24',
                         'LocalPort 22', 'Host example.test', 'all']:
            with self.subTest(selector=selector):
                self.main.write_text(f'  mAtCh {selector}\n')
                with self.assertRaises(ValueError):
                    self.check()

    def test_recursive_relative_glob_includes_are_checked(self):
        self.main.write_text('Include snippets/*.conf\n')
        self.write('snippets/first.conf', 'Include nested/*.conf\n')
        self.write('nested/override.conf', 'Match User root\nPermitRootLogin yes\n')
        with self.assertRaisesRegex(ValueError, 'override.conf:1'):
            self.check()

    def test_quoted_absolute_multiple_includes_are_checked(self):
        benign = self.write('benign.conf', 'PermitRootLogin no\n')
        override = self.write('custom path/override.conf', 'Match all\n')
        self.main.write_text(f'Include "{benign}" "{override}" # comment\n')
        with self.assertRaisesRegex(ValueError, 'override.conf:1'):
            self.check()

    def test_unreferenced_files_and_unmatched_globs_are_ignored(self):
        self.main.write_text('Include missing/*.conf\n')
        self.write('not-included.conf', 'Match all\n')
        self.check()

    def test_include_cycles_fail_closed(self):
        self.main.write_text('Include sshd_config\n')
        with self.assertRaisesRegex(ValueError, 'recursive'):
            self.check()

    def test_bad_include_quoting_fails_closed(self):
        self.main.write_text('Include "unterminated\n')
        with self.assertRaises(ValueError):
            self.check()

    def test_unsupported_include_syntax_fails_closed(self):
        for pattern in ["'custom.conf'", r'custom\ path.conf', '~/custom.conf',
                        '${CONFIG}/custom.conf', '{first,second}.conf']:
            with self.subTest(pattern=pattern):
                self.main.write_text(f'Include {pattern}\n')
                with self.assertRaises(ValueError):
                    self.check()

    def test_symlinked_include_is_checked(self):
        target = self.write('outside/override.conf', 'Match User root\n')
        (self.root / 'linked.conf').symlink_to(target)
        self.main.write_text('Include linked.conf\n')
        with self.assertRaises(ValueError):
            self.check()

    @unittest.skipUnless(shutil.which('sshd') and shutil.which('ssh-keygen'),
                         'OpenSSH tools are required for native reproduction')
    def test_native_sshd_reproduces_hidden_root_override(self):
        key = self.root / 'host_key'
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(key)],
                       check=True, capture_output=True, text=True)
        managed = (REPO / 'roles/ssh_config/templates/00-server-auto-config.conf.j2').read_text()
        self.main.write_text(
            f'HostKey {key}\n' + managed.replace('{{ ssh_port }}', '22')
            + '\nMatch User root\nPermitRootLogin prohibit-password\n'
        )
        command = [shutil.which('sshd'), '-T', '-f', str(self.main)]
        global_config = subprocess.run(command, check=True, capture_output=True, text=True).stdout
        for setting in ['permitrootlogin no', 'pubkeyauthentication yes',
                        'authenticationmethods publickey', 'passwordauthentication no',
                        'kbdinteractiveauthentication no']:
            self.assertIn(setting, global_config.splitlines())
        root_config = subprocess.run(
            command + ['-C', 'user=root,host=example.test,addr=192.0.2.1'],
            check=True, capture_output=True, text=True,
        ).stdout
        self.assertNotIn('permitrootlogin no', root_config.splitlines())
        with self.assertRaises(ValueError):
            self.check()

    def check_mode_run(self):
        tasks = yaml.safe_load(TASKS.read_text())
        first = tasks[0].copy()
        first['script'] = {'cmd': f'{SCANNER} {self.main}', 'executable': sys.executable}
        selected = [first] + tasks[-3:]
        for task in selected:
            task['become'] = False
        playbook = self.root / 'check-mode.yml'
        playbook.write_text(yaml.safe_dump([{
            'name': 'Check-mode SSH regression', 'hosts': 'localhost',
            'connection': 'local', 'gather_facts': False, 'tasks': selected,
        }]))
        environment = dict(os.environ,
                           ANSIBLE_LOCAL_TEMP=str(self.root / 'local-tmp'),
                           ANSIBLE_REMOTE_TEMP=str(self.root / 'remote-tmp'),
                           ANSIBLE_NOCOLOR='1',
                           ANSIBLE_INVENTORY_ENABLED='host_list')
        return subprocess.run(
            ['ansible-playbook', '-i', 'localhost,', str(playbook), '--check'],
            env=environment, capture_output=True, text=True,
        )

    def test_check_mode_skips_probe_and_both_post_change_assertions(self):
        result = self.check_mode_run()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('skipped=3', result.stdout)
        self.assertIn('changed=0', result.stdout)

    def test_check_mode_still_rejects_retained_match_rules(self):
        self.main.write_text('Match User root\nPermitRootLogin yes\n')
        result = self.check_mode_run()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('retained Match rules are not supported', result.stdout + result.stderr)

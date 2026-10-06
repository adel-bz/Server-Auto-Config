"""Exercise real firewall task validation and loops without changing a firewall."""

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

import yaml


REPO = Path(__file__).resolve().parents[1]
ROLE = REPO / 'roles/firewall'

# Stand in for UFW only; task arguments, conditions and loops remain unchanged.
MOCK_UFW = '''
from ansible.module_utils.basic import AnsibleModule

module = AnsibleModule(
    argument_spec={
        'rule': {'type': 'str', 'choices': ['allow']},
        'port': {'type': 'str'},
        'proto': {'type': 'str', 'choices': ['tcp', 'udp']},
        'state': {'type': 'str', 'choices': ['enabled']},
    },
    supports_check_mode=True,
)
module.exit_json(changed=False, observed=module.params)
'''


class FirewallTests(unittest.TestCase):
    def run_role(self, ports=None, use_defaults=False, check_mode=False, ssh_port=22):
        with tempfile.TemporaryDirectory(prefix='firewall-role-test-') as directory:
            root = Path(directory)
            module = root / 'mock_ufw.py'
            module.write_text(MOCK_UFW)
            tasks = yaml.safe_load((ROLE / 'tasks/main.yaml').read_text())
            selected = []
            registers = ['configured_rules', 'ssh_rule', 'enable_firewall']
            for task in tasks:
                if 'ansible.builtin.apt' in task:
                    continue  # No package installs or become operations in tests.
                task['become'] = False
                if 'community.general.ufw' in task:
                    task['mock_ufw'] = task.pop('community.general.ufw')
                    task['register'] = registers.pop(0)
                selected.append(task)
            results = root / 'results.json'
            selected.append({
                'name': 'Record simulated UFW requests',
                'ansible.builtin.copy': {
                    'dest': str(results), 'mode': '0600',
                    'content': "{{ {'configured': configured_rules, 'ssh': ssh_rule, "
                               "'enable': enable_firewall} | to_json }}",
                },
                'check_mode': False,
            })
            variables = yaml.safe_load((ROLE / 'defaults/main.yml').read_text())
            if not use_defaults:
                variables['firewall_allowed_ports'] = ports
            variables['ssh_port'] = ssh_port
            playbook = root / 'playbook.yml'
            playbook.write_text(yaml.safe_dump([{
                'hosts': 'localhost', 'connection': 'local', 'gather_facts': False,
                'vars': variables, 'tasks': selected,
            }]))
            environment = dict(os.environ,
                               ANSIBLE_LOCAL_TEMP=str(root / 'local-tmp'),
                               ANSIBLE_REMOTE_TEMP=str(root / 'remote-tmp'),
                               ANSIBLE_NOCOLOR='1',
                               ANSIBLE_INVENTORY_ENABLED='host_list')
            command = ['ansible-playbook', '-i', 'localhost,', '-M', str(root), str(playbook)]
            if check_mode:
                command.append('--check')
            result = subprocess.run(command, env=environment, capture_output=True, text=True)
            data = json.loads(results.read_text()) if results.exists() else None
            return result, data

    def assert_rules(self, ports, expected, **options):
        result, data = self.run_role(ports, **options)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        calls = data['configured'].get('results', [])
        observed = [(entry['observed']['port'], entry['observed']['proto']) for entry in calls]
        self.assertEqual(observed, expected)
        self.assertEqual(data['ssh']['observed']['proto'], 'tcp')
        self.assertEqual(data['ssh']['observed']['port'], str(options.get('ssh_port', 22)))
        self.assertEqual(data['enable']['observed']['state'], 'enabled')

    def test_multiple_ports_allow_both_protocols(self):
        ports = [7600, 80, 443, 8080]
        self.assert_rules(ports, [(str(port), proto) for port in ports for proto in ['tcp', 'udp']])

    def test_single_service_port_and_independent_ssh(self):
        self.assert_rules([7600], [('7600', 'tcp'), ('7600', 'udp')], ssh_port=2222)

    def test_empty_list_preserves_ssh_access(self):
        self.assert_rules([], [], ssh_port=2222)

    def test_default_ports_allow_http_and_https_both_protocols(self):
        self.assert_rules(None, [('80', 'tcp'), ('80', 'udp'), ('443', 'tcp'), ('443', 'udp')],
                          use_defaults=True)

    def test_duplicate_numeric_and_string_ports_are_normalized(self):
        self.assert_rules([7600, '7600', '443'],
                          [('7600', 'tcp'), ('7600', 'udp'), ('443', 'tcp'), ('443', 'udp')])

    def test_check_mode_supports_rule_planning(self):
        self.assert_rules([7600], [('7600', 'tcp'), ('7600', 'udp')], check_mode=True)

    def test_non_list_values_are_rejected_before_ufw(self):
        for ports in [7600, '7600, 80, 443', {'port': 7600}, None]:
            with self.subTest(ports=ports):
                result, data = self.run_role(ports)
                self.assertNotEqual(result.returncode, 0)
                self.assertIsNone(data)
                self.assertNotIn('TASK [Allow configured firewall ports', result.stdout)

    def test_invalid_ports_are_rejected_before_ufw(self):
        for port in [0, 65536, -1, True, 1.5, '80/tcp', '7600, 80']:
            with self.subTest(port=port):
                result, data = self.run_role([port])
                self.assertNotEqual(result.returncode, 0)
                self.assertIsNone(data)
                self.assertNotIn('TASK [Allow configured firewall ports', result.stdout)

    def test_invalid_ssh_port_is_rejected_before_ufw(self):
        result, data = self.run_role([7600], ssh_port='22/tcp')
        self.assertNotEqual(result.returncode, 0)
        self.assertIsNone(data)

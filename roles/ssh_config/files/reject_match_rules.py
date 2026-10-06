#!/usr/bin/env python3
"""Fail closed on retained Match blocks, following SSH Include directives.

This preflight does not replace sshd's syntax/effective-policy validation.
It deliberately rejects all Match blocks rather than sampling connections.
"""

import glob
from pathlib import Path
import re
import shlex
import sys


def reject_match_rules(config, include_root=Path('/etc/ssh'), ancestors=()):
    """Inspect the main file and recursive includes without modifying them."""
    config = Path(config).resolve(strict=True)
    if config in ancestors or len(ancestors) >= 16:
        raise ValueError(f'{config}: recursive or excessively nested SSH Include')
    ancestors = (*ancestors, config)

    for number, line in enumerate(config.read_text().splitlines(), 1):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        keyword, *arguments = re.split(r'[ \t=]+', line, maxsplit=1)
        keyword = keyword.lower()
        if keyword == 'match':
            raise ValueError(
                f'{config}:{number}: retained Match rules are not supported. '
                'Review and remove or migrate this connection-specific policy '
                'before applying SSH hardening; no SSH configuration was changed '
                'by this preflight.'
            )
        if keyword != 'include':
            continue
        if not arguments:
            raise ValueError(f'{config}:{number}: Include has no path')
        # Do not silently misinterpret uncommon escaping/expansion syntax.
        # The preflight must fail closed rather than skip a file sshd may read.
        if '\\' in arguments[0] or "'" in arguments[0]:
            raise ValueError(f'{config}:{number}: unsupported SSH Include escaping')
        # OpenSSH supports quoted paths and trailing comment arguments.
        for pattern in shlex.split(arguments[0], comments=False):
            if pattern.startswith('#'):
                break
            if pattern.startswith('~') or any(token in pattern for token in '${}%'):
                raise ValueError(f'{config}:{number}: unsupported SSH Include expansion')
            path = Path(pattern)
            if not path.is_absolute():
                path = Path(include_root) / path
            # Like sshd, unmatched Include globs contribute no configuration.
            for included in sorted(glob.glob(str(path))):
                reject_match_rules(included, include_root, ancestors)


if __name__ == '__main__':
    try:
        reject_match_rules(sys.argv[1])
    except (OSError, ValueError, IndexError) as error:
        print(f'SSH policy preflight failed: {error}', file=sys.stderr)
        sys.exit(1)

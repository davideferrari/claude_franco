#!/usr/bin/env python3
"""Run every Franco test file in its own interpreter and report the total.

Run: py -3 tests/run_all.py
"""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SUITES = ["test_franco.py", "test_daemon.py", "test_hooks.py"]

failed = []
for suite in SUITES:
    print("== %s" % suite)
    result = subprocess.run([sys.executable, os.path.join(HERE, suite)])
    if result.returncode != 0:
        failed.append(suite)
    print()

if failed:
    print("FAILED: %s" % ", ".join(failed))
    sys.exit(1)
print("all suites passed (%s)" % sys.version.split()[0])

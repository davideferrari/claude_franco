#!/usr/bin/env python3
"""SessionEnd hook: stop any audio still playing. The daemon itself stays warm
so the next session starts speaking with zero cold-start."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import franco_common as fc  # noqa: E402


def main():
    fc.read_stdin_json()
    if fc.is_enabled():
        fc.post_to_daemon("/silence", {}, timeout=1.0)


if __name__ == "__main__":
    main()
    sys.exit(0)

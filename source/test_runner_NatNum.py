#!/usr/bin/env python3
"""Compatibility entry point for the natural-number proof fixture suite.

The shared fixture validator now owns suite discovery, theory resources,
validation, and reporting. Keep this historical command as a thin wrapper so
existing invocations continue to work without maintaining a second runner.
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path


_VALIDATOR = Path(__file__).with_name("validate_all_proofs.py")


if __name__ == "__main__":
    sys.argv = [
        str(_VALIDATOR),
        "--suite",
        "testProofsNat",
        *sys.argv[1:],
    ]
    runpy.run_path(str(_VALIDATOR), run_name="__main__")

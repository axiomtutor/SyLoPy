


import pytest

from .support import *  # noqa: F401,F403


def pytest_addoption(parser):
    parser.addoption(
        "--extended",
        action="store_true",
        default=False,
        help="run the full Python test suite, including extended audits",
    )


def pytest_collection_modifyitems(config, items):
    markexpr = getattr(config.option, "markexpr", "")
    if "extended" in markexpr:
        return
    if config.getoption("--extended"):
        return

    skip_extended = pytest.mark.skip(
        reason="extended audit test; request explicitly with --extended or -m extended"
    )
    for item in items:
        if item.get_closest_marker("extended"):
            item.add_marker(skip_extended)

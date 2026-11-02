


import pytest

from .support import *  # noqa: F401,F403


def pytest_addoption(parser):
    parser.addoption(
        "--extended",
        action="store_true",
        default=False,
        help="run the full Python test suite, including extended audits",
    )
    parser.addoption(
        "--suite",
        action="store",
        choices=("default", "extended", "all"),
        default=None,
        help="run a named Python test suite",
    )

def pytest_collection_modifyitems(config, items):
    markexpr = getattr(config.option, "markexpr", "")
    suite = config.getoption("--suite")

    for item in items:
        module_name = item.nodeid.rsplit("::", 1)[0]
        # Red-team findings and audit/mutation tools are deliberately outside
        # the PR/local default batch, even though they remain in the all suite.
        if ("red_team" in module_name or "_audit" in module_name
                or "mutation_check_tool" in module_name):
            item.add_marker(pytest.mark.extended)
        extended = item.get_closest_marker("extended") is not None
        if not extended:
            item.add_marker(pytest.mark.default)

    if markexpr:
        return
    if config.getoption("--extended") or suite == "all":
        return

    skip_unselected = pytest.mark.skip(
        reason="test is outside the selected named suite; request explicitly with --suite"
    )
    for item in items:
        if suite == "extended":
            if not item.get_closest_marker("extended"):
                item.add_marker(skip_unselected)
        elif suite == "default" or suite is None:
            if item.get_closest_marker("extended"):
                item.add_marker(skip_unselected)

"""Package-level sanity tests that run with or without the compiled kernel."""

import pytest

import traffic_sim
from traffic_sim import kernel


def test_version() -> None:
    """The package exposes its version."""
    assert traffic_sim.__version__ == "0.1.0"


def test_missing_kernel_raises_with_install_hint() -> None:
    """Without the compiled kernel, accessors fail with an actionable message."""
    if kernel.kernel_available():
        pytest.skip("compiled kernel is installed")
    with pytest.raises(ModuleNotFoundError, match="core/bindings"):
        kernel.new_simulation(0)

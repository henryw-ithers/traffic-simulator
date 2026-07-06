"""Package-level sanity tests that run with or without the compiled kernel."""

import pytest

import traffic_sim
from traffic_sim import kernel


def test_version() -> None:
    assert traffic_sim.__version__ == "0.1.0"


def test_missing_kernel_raises_with_install_hint() -> None:
    if kernel.kernel_available():
        pytest.skip("compiled kernel is installed")
    with pytest.raises(ModuleNotFoundError, match="core/bindings"):
        kernel.new_simulation(0)

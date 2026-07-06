"""Access to the compiled simulation kernel (``traffic_sim_kernel``).

The kernel is an opaque handle with methods (ADR-0003): no per-entity Python
objects. Any convenience wrappers added here must stay thin layers over the
kernel's bulk/columnar accessors, never per-entity FFI calls.
"""

from __future__ import annotations

try:
    import traffic_sim_kernel as _kernel
except ModuleNotFoundError:
    _kernel = None

KERNEL_INSTALL_HINT = (
    "The compiled simulation kernel (traffic_sim_kernel) is not installed. "
    "From the repository root run: pip install ./core/bindings (or, for a "
    "Rust dev loop: maturin develop --manifest-path core/bindings/Cargo.toml)"
)


def kernel_available() -> bool:
    """Whether the compiled kernel extension is importable."""
    return _kernel is not None


def kernel_version() -> str:
    """Version of the installed compiled kernel."""
    if _kernel is None:
        raise ModuleNotFoundError(KERNEL_INSTALL_HINT)
    return _kernel.__version__


def new_simulation(seed: int):
    """Create a kernel simulation with an explicit seed.

    Stub API: grows toward ADR-0003's ``load(network, demand, seed)`` once the
    network and demand file formats exist.
    """
    if _kernel is None:
        raise ModuleNotFoundError(KERNEL_INSTALL_HINT)
    return _kernel.Simulation(seed)

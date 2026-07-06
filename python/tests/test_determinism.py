"""Determinism harness (stub) — Python side of ADR-0003 action item 4.

Guarantee under test: same seed + same inputs => byte-identical state at every
tick, on the same platform/binary (cross-platform runs are only statistically
equivalent — see the 2026-07-06 amendment to ADR-0003).

Currently the only inputs are the seed and tick count. As real inputs arrive
(network file, demand file), this harness must load pinned copies of them and
compare full result output, not just state digests.
"""

import subprocess
import sys

import pytest

from traffic_sim import kernel

pytestmark = pytest.mark.skipif(
    not kernel.kernel_available(), reason=kernel.KERNEL_INSTALL_HINT
)

SEED = 20260706
TICKS = 1000
DT = 0.1


def test_same_seed_identical_digest_at_every_tick() -> None:
    a = kernel.new_simulation(SEED)
    b = kernel.new_simulation(SEED)
    for tick in range(TICKS):
        a.step(DT)
        b.step(DT)
        assert a.state_digest() == b.state_digest(), f"state diverged at tick {tick}"


def test_different_seeds_diverge() -> None:
    a = kernel.new_simulation(1)
    b = kernel.new_simulation(2)
    a.step(DT)
    b.step(DT)
    assert a.state_digest() != b.state_digest()


_DIGEST_SCRIPT = """
import traffic_sim_kernel

sim = traffic_sim_kernel.Simulation({seed})
digests = []
for _ in range({ticks}):
    sim.step({dt})
    digests.append(sim.state_digest())
print(",".join(map(str, digests)))
"""


def test_identical_digest_sequence_across_processes() -> None:
    """Two separate OS processes must produce byte-identical digest sequences.

    Catches nondeterminism that in-process comparison can't (anything leaking
    in from environment or process state).
    """
    script = _DIGEST_SCRIPT.format(seed=SEED, ticks=200, dt=DT)
    runs = [
        subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        for _ in range(2)
    ]
    assert runs[0] == runs[1]

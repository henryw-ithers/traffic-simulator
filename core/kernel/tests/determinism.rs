//! Determinism harness (stub) — ADR-0003 action item 4.
//!
//! Guarantee under test: same seed + same inputs ⇒ byte-identical state at
//! **every tick** (not merely end-to-end), on the same platform/binary.
//!
//! Currently the only inputs are the seed and the tick count; as the kernel
//! gains real inputs (network file, demand file), this harness must grow to
//! load identical copies of them and compare full result output, not just the
//! state digest.

use sim_kernel::{Command, Simulation};

const TICKS: u64 = 1_000;
const DT: f64 = 0.1;

#[test]
fn same_seed_identical_digest_at_every_tick() {
    let mut a = Simulation::new(20260706);
    let mut b = Simulation::new(20260706);
    for tick in 0..TICKS {
        a.step(DT);
        b.step(DT);
        assert_eq!(
            a.state_digest(),
            b.state_digest(),
            "state diverged at tick {tick}"
        );
    }
}

#[test]
fn different_seeds_diverge() {
    let mut a = Simulation::new(1);
    let mut b = Simulation::new(2);
    a.step(DT);
    b.step(DT);
    assert_ne!(a.state_digest(), b.state_digest());
}

#[test]
fn queued_commands_do_not_break_tick_determinism() {
    // Identical command schedules must yield identical states; this pins the
    // command buffer into the determinism contract before real commands exist.
    let mut a = Simulation::new(99);
    let mut b = Simulation::new(99);
    for tick in 0..100 {
        if tick % 7 == 0 {
            a.queue_command(Command::Noop);
            b.queue_command(Command::Noop);
        }
        a.step(DT);
        b.step(DT);
        assert_eq!(a.state_digest(), b.state_digest());
    }
}

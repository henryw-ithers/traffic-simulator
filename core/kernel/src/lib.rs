//! Toronto Transportation Digital Twin — simulation kernel.
//!
//! This crate owns the tick-by-tick simulation loop. Python (the `/python`
//! package) handles data import, demand modeling, scenarios, evaluation, and
//! visualization, and calls into this kernel through the `traffic-sim-kernel`
//! PyO3 bindings crate.
//!
//! # Internal disciplines (ADR-0003 — requirements, not suggestions)
//!
//! The public API for v0.1 is batch-run only (load / run / results), but the
//! kernel's internals are committed to three disciplines from the first line
//! of code, so that Phase 2's tick-level control API is an additive change
//! rather than a restructuring. Code review should treat violations as bugs.
//!
//! 1. **The run loop is literally `for tick { step(dt) }`.** [`Simulation::run`]
//!    is a thin wrapper; [`Simulation::step`] never assumes knowledge of how
//!    many ticks remain or what happens between calls.
//! 2. **All mutations flow through a command buffer applied at tick
//!    boundaries** — including internal ones (e.g. the demand model releasing
//!    vehicles). Changes requested during a tick take effect at the next tick
//!    boundary, never mid-tick.
//! 3. **State is queryable at any tick, with stable entity IDs.** There is no
//!    separate accumulate-only-at-the-end representation.
//!
//! # Determinism (ADR-0003, amended 2026-07-06)
//!
//! Same seed + same inputs ⇒ byte-identical results at **tick granularity**,
//! on the same platform and binary. Cross-platform results are statistically
//! equivalent but not necessarily bit-identical. All stochastic behavior takes
//! an explicit seed; there is no unseeded global RNG state.

mod rng;

pub use rng::SplitMix64;

/// A mutation requested during a tick, applied at the next tick boundary.
///
/// Placeholder vocabulary: real commands (vehicle release, signal state
/// change, …) replace this as the kernel grows. The buffering discipline is
/// the point — see the crate docs.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Command {
    /// Does nothing; exists so the command-buffer path is exercised from day one.
    Noop,
}

/// A running simulation: the explicit `step(dt)` loop over world state.
///
/// The world state is currently a stub (tick counter + RNG stream). The entity
/// model (ECS per ADR-0002) lands here once the network format exists to load
/// something real.
#[derive(Debug)]
pub struct Simulation {
    seed: u64,
    tick: u64,
    rng: SplitMix64,
    command_buffer: Vec<Command>,
}

impl Simulation {
    /// Creates a simulation from an explicit seed.
    pub fn new(seed: u64) -> Self {
        Self {
            seed,
            tick: 0,
            rng: SplitMix64::new(seed),
            command_buffer: Vec::new(),
        }
    }

    /// Queues a command to be applied at the next tick boundary.
    pub fn queue_command(&mut self, command: Command) {
        self.command_buffer.push(command);
    }

    /// Advances the simulation by one tick of `dt` seconds.
    ///
    /// Buffered commands are applied at the start of the tick (the tick
    /// boundary), then the world advances. `step` must not assume anything
    /// about how many ticks remain or what happens between calls.
    pub fn step(&mut self, _dt: f64) {
        for command in self.command_buffer.drain(..) {
            match command {
                Command::Noop => {}
            }
        }
        // Placeholder for physics: draw from the seeded stream so the digest
        // evolves and determinism tests exercise real state.
        let _ = self.rng.next_u64();
        self.tick += 1;
    }

    /// Runs `ticks` ticks. A thin wrapper over [`Simulation::step`] — nothing more.
    pub fn run(&mut self, ticks: u64, dt: f64) {
        for _ in 0..ticks {
            self.step(dt);
        }
    }

    /// The seed this simulation was created with.
    pub fn seed(&self) -> u64 {
        self.seed
    }

    /// The number of ticks executed so far.
    pub fn tick(&self) -> u64 {
        self.tick
    }

    /// A digest of the complete simulation state at the current tick.
    ///
    /// Two simulations with the same seed and inputs must report identical
    /// digests at every tick on the same platform/binary. As real state
    /// (vehicles, signals, …) is added to the kernel it must be folded into
    /// this digest, in a documented, stable order.
    pub fn state_digest(&self) -> u64 {
        let mut digest = Fnv1a::new();
        digest.write_u64(self.tick);
        digest.write_u64(self.rng.state());
        digest.finish()
    }
}

/// FNV-1a, 64-bit: a simple, dependency-free, platform-independent hash for
/// the state digest. Not cryptographic; collisions merely weaken a test.
struct Fnv1a(u64);

impl Fnv1a {
    fn new() -> Self {
        Self(0xcbf2_9ce4_8422_2325)
    }

    fn write_u64(&mut self, value: u64) {
        for byte in value.to_le_bytes() {
            self.0 ^= u64::from(byte);
            self.0 = self.0.wrapping_mul(0x0000_0100_0000_01b3);
        }
    }

    fn finish(&self) -> u64 {
        self.0
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn commands_apply_at_tick_boundary_not_immediately() {
        let mut sim = Simulation::new(7);
        sim.queue_command(Command::Noop);
        assert_eq!(sim.command_buffer.len(), 1, "queued, not applied");
        sim.step(0.1);
        assert!(sim.command_buffer.is_empty(), "drained at the boundary");
    }

    #[test]
    fn run_is_a_thin_wrapper_over_step() {
        let mut stepped = Simulation::new(42);
        let mut ran = Simulation::new(42);
        for _ in 0..100 {
            stepped.step(0.1);
        }
        ran.run(100, 0.1);
        assert_eq!(stepped.tick(), ran.tick());
        assert_eq!(stepped.state_digest(), ran.state_digest());
    }
}

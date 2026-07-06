//! Seeded RNG for the kernel.
//!
//! SplitMix64 (public domain, Vigna) implemented inline as a **placeholder**:
//! integer-only, so its stream is bit-identical across platforms, and
//! dependency-free. Choosing a real RNG crate (e.g. `rand` + `rand_chacha`) is
//! a deliberate dependency decision to make when the kernel gains real
//! stochastic behavior — see ADR-0006.

/// A seeded, deterministic pseudo-random number generator (SplitMix64).
#[derive(Debug, Clone)]
pub struct SplitMix64 {
    state: u64,
}

impl SplitMix64 {
    /// Creates a generator from an explicit seed. Never seed from ambient
    /// state (time, thread ID, …) — reproducibility is a project principle.
    pub fn new(seed: u64) -> Self {
        Self { state: seed }
    }

    /// Returns the next value in the stream.
    pub fn next_u64(&mut self) -> u64 {
        self.state = self.state.wrapping_add(0x9e37_79b9_7f4a_7c15);
        let mut z = self.state;
        z = (z ^ (z >> 30)).wrapping_mul(0xbf58_476d_1ce4_e5b9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94d0_49bb_1331_11eb);
        z ^ (z >> 31)
    }

    /// The raw generator state, for inclusion in the simulation state digest.
    pub fn state(&self) -> u64 {
        self.state
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn known_answer_from_reference_implementation() {
        // First three outputs for seed 0, per Vigna's reference splitmix64.c.
        let mut rng = SplitMix64::new(0);
        assert_eq!(rng.next_u64(), 0xe220_a839_7b1d_cdaf);
        assert_eq!(rng.next_u64(), 0x6e78_9e6a_a1b9_65f4);
        assert_eq!(rng.next_u64(), 0x06c4_5d18_8009_454f);
    }

    #[test]
    fn same_seed_same_stream() {
        let mut a = SplitMix64::new(123);
        let mut b = SplitMix64::new(123);
        for _ in 0..1000 {
            assert_eq!(a.next_u64(), b.next_u64());
        }
    }
}

//! PyO3 bindings: the `traffic_sim_kernel` Python extension module.
//!
//! Deliberately thin (ADR-0003): opaque handles with methods, no per-entity
//! Python objects, and — once results exist — bulk columnar transfer only.
//! Simulation logic lives in the `sim-kernel` crate, never here.

use pyo3::prelude::*;

/// A running simulation (opaque handle over the kernel's `Simulation`).
#[pyclass(name = "Simulation")]
struct PySimulation {
    inner: sim_kernel::Simulation,
}

#[pymethods]
impl PySimulation {
    /// Create a simulation from an explicit seed.
    #[new]
    fn new(seed: u64) -> Self {
        Self {
            inner: sim_kernel::Simulation::new(seed),
        }
    }

    /// Advance one tick of `dt` seconds.
    fn step(&mut self, dt: f64) {
        self.inner.step(dt);
    }

    /// Run `ticks` ticks of `dt` seconds each.
    fn run(&mut self, ticks: u64, dt: f64) {
        self.inner.run(ticks, dt);
    }

    /// Seed the simulation was created with.
    #[getter]
    fn seed(&self) -> u64 {
        self.inner.seed()
    }

    /// Number of ticks executed so far.
    #[getter]
    fn tick(&self) -> u64 {
        self.inner.tick()
    }

    /// Digest of the complete simulation state at the current tick.
    /// Same seed + same inputs ⇒ same digest at every tick, per platform/binary.
    fn state_digest(&self) -> u64 {
        self.inner.state_digest()
    }

    fn __repr__(&self) -> String {
        format!(
            "Simulation(seed={}, tick={})",
            self.inner.seed(),
            self.inner.tick()
        )
    }
}

#[pymodule]
fn traffic_sim_kernel(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PySimulation>()?;
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    Ok(())
}

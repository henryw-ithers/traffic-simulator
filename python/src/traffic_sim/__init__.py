"""Toronto Transportation Digital Twin — Python periphery.

Data import, demand modeling, scenario engine, evaluation, and visualization
live in this package. Simulation physics lives in the Rust kernel (``/core``)
and is reached through the compiled ``traffic_sim_kernel`` bindings — this
package must never reimplement it (see AGENTS.md).
"""

__version__ = "0.1.0"

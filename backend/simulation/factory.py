"""
Simulation Factory Module.
Maps architecture IDs to specialized simulation classes and provides factory instantiation.
"""

from typing import Dict, Type
from simulation.base import BaseSimulation
from simulation.single_server import SingleServerSimulation
from simulation.load_balanced import LoadBalancedSimulation
from simulation.auto_scaling import AutoScalingSimulation
from simulation.three_tier import ThreeTierSimulation


ARCHITECTURE_SIMULATION_REGISTRY: Dict[str, Type[BaseSimulation]] = {
    "single_server": SingleServerSimulation,
    "load_balanced": LoadBalancedSimulation,
    "auto_scaling": AutoScalingSimulation,
    "three_tier": ThreeTierSimulation,
}


def get_simulation_class(arch_id: str) -> Type[BaseSimulation]:
    """
    Retrieve the simulation class corresponding to an architecture ID.
    Falls back to BaseSimulation or LoadBalancedSimulation if unmatched.
    """
    sim_class = ARCHITECTURE_SIMULATION_REGISTRY.get(arch_id)
    if not sim_class:
        raise ValueError(f"No simulation class registered for architecture: {arch_id}")
    return sim_class


def create_simulation(arch_config: dict, scenario_config: dict) -> BaseSimulation:
    """
    Factory function to instantiate the corresponding simulation class
    for the provided architecture configuration.
    """
    arch_id = arch_config.get("id")
    sim_cls = get_simulation_class(arch_id)
    return sim_cls(arch_config, scenario_config)

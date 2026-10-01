"""
Simulation Engine Entrypoint and Polymorphic Interface.
Provides unified access to the specialized architecture simulation classes.
"""

from typing import Type
from simulation.base import Server, LoadBalancer, MetricsCollector, BaseSimulation
from simulation.single_server import SingleServerSimulation
from simulation.load_balanced import LoadBalancedSimulation
from simulation.auto_scaling import AutoScalingSimulation
from simulation.three_tier import ThreeTierSimulation
from simulation.factory import (
    ARCHITECTURE_SIMULATION_REGISTRY,
    get_simulation_class,
    create_simulation,
)


class CloudSimulation:
    """
    Polymorphic simulation runner.
    Instantiates and returns the appropriate architecture-specific simulation instance
    (SingleServerSimulation, LoadBalancedSimulation, AutoScalingSimulation, or ThreeTierSimulation)
    based on the provided architecture configuration.
    """

    def __new__(cls, arch_config: dict, scenario_config: dict) -> BaseSimulation:
        return create_simulation(arch_config, scenario_config)


__all__ = [
    "Server",
    "LoadBalancer",
    "MetricsCollector",
    "BaseSimulation",
    "SingleServerSimulation",
    "LoadBalancedSimulation",
    "AutoScalingSimulation",
    "ThreeTierSimulation",
    "ARCHITECTURE_SIMULATION_REGISTRY",
    "get_simulation_class",
    "create_simulation",
    "CloudSimulation",
]

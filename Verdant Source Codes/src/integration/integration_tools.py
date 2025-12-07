from typing import Any
from .BlockIntegrationManager import BlockIntegrationManager
from .SystemIntegrationFramework import SystemIntegrationFramework
from .IntegrationTestSuite import IntegrationTestSuite


def integrate_system_tools(system: Any) -> Any:
    """
    Initialize and attach integration tools to the Unified System.

    This function sets up the integration testing and monitoring infrastructure
    for the system, including:
    - BlockIntegrationManager for tracking block interactions
    - SystemIntegrationFramework for comprehensive integration testing
    - IntegrationTestSuite for running integration tests

    Args:
        system: The Unified Synthetic Mind system instance

    Returns:
        The system instance with integrated tools attached
    """
    # Initialize Block Integration Manager
    system.integration_manager = BlockIntegrationManager(system)

    # Initialize System Integration Framework
    system.integration_tools = SystemIntegrationFramework(system)

    # Initialize Integration Test Suite
    system.integration_test_suite = IntegrationTestSuite(
        system,
        system.integration_manager
    )

    return system

from typing import Any

from .BlockIntegrationManager import BlockIntegrationManager
from .IntegrationTestSuite import IntegrationTestSuite
from .SystemIntegrationFramework import create_integration_testing_module


def integrate_system_tools(system: Any):
    """Attach integration-related utilities to the system."""
    # Initialize integration manager and test suite
    integration_manager = BlockIntegrationManager(system)
    integration_framework = create_integration_testing_module(system)
    integration_test_suite = IntegrationTestSuite(system, integration_manager)

    # Attach to system for easy access
    system.integration_manager = integration_manager
    system.integration_tools = integration_framework
    system.integration_test_suite = integration_test_suite

    return system

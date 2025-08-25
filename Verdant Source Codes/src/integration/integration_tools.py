"""Utility functions for wiring integration components into the Unified System."""

from .BlockIntegrationManager import BlockIntegrationManager
from .SystemIntegrationFramework import SystemIntegrationFramework
from .IntegrationTestSuite import IntegrationTestSuite


def integrate_system_tools(system):
    """Attach integration helpers to the provided system instance.

    The UnifiedSystem expects this helper to create integration-related
    objects and attach them as attributes.  The original repository was
    missing this module which caused a ``ModuleNotFoundError`` during
    system initialisation.  This implementation wires up the integration
    manager, integration framework and integration test suite.

    Args:
        system: The ``UnifiedSystem`` instance that requires integration
            utilities.

    Returns:
        The same ``system`` instance with new attributes:
        ``integration_manager``, ``integration_framework`` and
        ``integration_tests``.
    """
    integration_manager = BlockIntegrationManager(system)
    integration_framework = SystemIntegrationFramework(system)
    integration_tests = IntegrationTestSuite(system, integration_manager)

    # Expose the helpers on the system for later use
    system.integration_manager = integration_manager
    system.integration_framework = integration_framework
    system.integration_tests = integration_tests
    return system

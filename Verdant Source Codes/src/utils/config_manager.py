"""
Configuration Management for Verdant-Minds

This module provides configuration loading, validation, and management
functionality for the Verdant-Minds system.

Features:
- Load configuration from YAML files
- Merge configurations (default + custom + override)
- Validate configuration parameters
- Type checking and range validation
- Environment variable support
- Configuration hot-reloading (optional)

Usage:
    >>> from src.utils.config_manager import ConfigManager
    >>> config = ConfigManager()
    >>> config.load("my_config.yaml")
    >>> ecwf_dims = config.get("ecwf.cognitive_dimensions")
    >>> config.validate()
"""

import os
import yaml
import copy
from typing import Any, Dict, List, Optional, Union
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""
    pass


class ConfigManager:
    """
    Manages configuration for Verdant-Minds system.

    Supports:
    - Default configuration
    - Custom configuration files
    - Runtime overrides
    - Validation
    - Nested access with dot notation
    """

    def __init__(
        self,
        config_path: Optional[str] = None,
        config_override: Optional[Dict[str, Any]] = None,
        validate_on_load: bool = True
    ):
        """
        Initialize configuration manager.

        Args:
            config_path: Path to custom config file (optional)
            config_override: Dictionary of config overrides (optional)
            validate_on_load: Whether to validate immediately
        """
        self.config: Dict[str, Any] = {}
        self._default_config_path = self._find_default_config()

        # Load default configuration
        self._load_default()

        # Load custom configuration if provided
        if config_path:
            self.load(config_path)

        # Apply overrides if provided
        if config_override:
            self.update(config_override)

        # Validate if requested
        if validate_on_load:
            self.validate()

    def _find_default_config(self) -> str:
        """Find the default configuration file."""
        # Try several possible locations
        possible_paths = [
            Path(__file__).parent.parent.parent / "config" / "default_config.yaml",
            Path("Verdant Source Codes/config/default_config.yaml"),
            Path("config/default_config.yaml"),
        ]

        for path in possible_paths:
            if path.exists():
                return str(path)

        raise FileNotFoundError(
            "Could not find default_config.yaml. "
            "Please ensure it exists in the config/ directory."
        )

    def _load_default(self):
        """Load the default configuration."""
        try:
            with open(self._default_config_path, 'r') as f:
                self.config = yaml.safe_load(f)
            logger.info(f"Loaded default configuration from {self._default_config_path}")
        except Exception as e:
            raise RuntimeError(f"Failed to load default configuration: {e}")

    def load(self, config_path: str):
        """
        Load and merge a custom configuration file.

        Args:
            config_path: Path to YAML configuration file
        """
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        try:
            with open(config_path, 'r') as f:
                custom_config = yaml.safe_load(f)

            # Merge with existing configuration
            self.config = self._deep_merge(self.config, custom_config)
            logger.info(f"Loaded and merged configuration from {config_path}")

        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in configuration file: {e}")
        except Exception as e:
            raise RuntimeError(f"Failed to load configuration: {e}")

    def update(self, overrides: Dict[str, Any]):
        """
        Update configuration with dictionary of overrides.

        Args:
            overrides: Dictionary of configuration overrides
                      Can use dot notation for nested keys

        Example:
            >>> config.update({
            ...     "ecwf.cognitive_dimensions": 7,
            ...     "logging.level": "DEBUG"
            ... })
        """
        # Convert flat dict with dot notation to nested dict
        nested_overrides = self._flatten_to_nested(overrides)

        # Merge with existing configuration
        self.config = self._deep_merge(self.config, nested_overrides)
        logger.debug(f"Applied configuration overrides: {overrides}")

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation.

        Args:
            key: Configuration key (supports dot notation)
            default: Default value if key not found

        Returns:
            Configuration value or default

        Example:
            >>> config.get("ecwf.cognitive_dimensions")
            5
            >>> config.get("nonexistent.key", default=42)
            42
        """
        keys = key.split('.')
        value = self.config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key: str, value: Any):
        """
        Set configuration value using dot notation.

        Args:
            key: Configuration key (supports dot notation)
            value: Value to set

        Example:
            >>> config.set("ecwf.cognitive_dimensions", 7)
        """
        keys = key.split('.')
        current = self.config

        for k in keys[:-1]:
            if k not in current or not isinstance(current[k], dict):
                current[k] = {}
            current = current[k]

        current[keys[-1]] = value
        logger.debug(f"Set config: {key} = {value}")

    def validate(self) -> bool:
        """
        Validate the current configuration.

        Raises:
            ConfigValidationError: If validation fails

        Returns:
            True if validation succeeds
        """
        errors = []

        # System validation
        errors.extend(self._validate_system())

        # ECWF validation
        errors.extend(self._validate_ecwf())

        # Memory Web validation
        errors.extend(self._validate_memory_web())

        # Blocks validation
        errors.extend(self._validate_blocks())

        # Governance validation
        errors.extend(self._validate_governance())

        # Logging validation
        errors.extend(self._validate_logging())

        if errors:
            error_msg = "Configuration validation failed:\n" + "\n".join(
                f"  - {e}" for e in errors
            )
            raise ConfigValidationError(error_msg)

        logger.info("Configuration validation passed")
        return True

    def _validate_system(self) -> List[str]:
        """Validate system configuration."""
        errors = []

        seed = self.get("system.seed")
        if seed is not None and not isinstance(seed, int):
            errors.append("system.seed must be an integer or null")

        debug = self.get("system.debug")
        if not isinstance(debug, bool):
            errors.append("system.debug must be a boolean")

        max_concurrent = self.get("system.max_concurrent_chunks")
        if not isinstance(max_concurrent, int) or max_concurrent < 1:
            errors.append("system.max_concurrent_chunks must be a positive integer")

        return errors

    def _validate_ecwf(self) -> List[str]:
        """Validate ECWF configuration."""
        errors = []

        cog_dims = self.get("ecwf.cognitive_dimensions")
        if not isinstance(cog_dims, int) or cog_dims < 1:
            errors.append("ecwf.cognitive_dimensions must be a positive integer")

        eth_dims = self.get("ecwf.ethical_dimensions")
        if not isinstance(eth_dims, int) or eth_dims < 1:
            errors.append("ecwf.ethical_dimensions must be a positive integer")

        init_amp = self.get("ecwf.initial_amplitude")
        if not isinstance(init_amp, (int, float)) or init_amp <= 0:
            errors.append("ecwf.initial_amplitude must be a positive number")

        entropy_base = self.get("ecwf.entropy_base")
        if not isinstance(entropy_base, (int, float)) or entropy_base <= 1:
            errors.append("ecwf.entropy_base must be > 1")

        return errors

    def _validate_memory_web(self) -> List[str]:
        """Validate Memory Web configuration."""
        errors = []

        graph_type = self.get("memory_web.graph_type")
        if graph_type not in ["directed", "undirected"]:
            errors.append("memory_web.graph_type must be 'directed' or 'undirected'")

        stability = self.get("memory_web.default_stability")
        if not isinstance(stability, (int, float)) or not 0 <= stability <= 1:
            errors.append("memory_web.default_stability must be in [0, 1]")

        activation_threshold = self.get("memory_web.activation_threshold")
        if not isinstance(activation_threshold, (int, float)) or not 0 <= activation_threshold <= 1:
            errors.append("memory_web.activation_threshold must be in [0, 1]")

        max_hops = self.get("memory_web.max_activation_hops")
        if not isinstance(max_hops, int) or max_hops < 1:
            errors.append("memory_web.max_activation_hops must be a positive integer")

        return errors

    def _validate_blocks(self) -> List[str]:
        """Validate block configurations."""
        errors = []

        # Validate each block's enabled status
        block_names = [
            "sensory_input", "pattern_recognition", "memory_storage",
            "internal_communication", "reasoning_planning", "ethics_values",
            "action_selection", "language_processing", "continual_learning"
        ]

        for block_name in block_names:
            enabled = self.get(f"blocks.{block_name}.enabled")
            if not isinstance(enabled, bool):
                errors.append(f"blocks.{block_name}.enabled must be a boolean")

        # Validate specific block parameters
        max_keywords = self.get("blocks.pattern_recognition.max_keywords")
        if not isinstance(max_keywords, int) or max_keywords < 1:
            errors.append("blocks.pattern_recognition.max_keywords must be a positive integer")

        ethical_sensitivity = self.get("blocks.ethics_values.ethical_sensitivity")
        if not isinstance(ethical_sensitivity, (int, float)) or not 0 <= ethical_sensitivity <= 1:
            errors.append("blocks.ethics_values.ethical_sensitivity must be in [0, 1]")

        learning_rate = self.get("blocks.continual_learning.learning_rate")
        if not isinstance(learning_rate, (int, float)) or learning_rate <= 0:
            errors.append("blocks.continual_learning.learning_rate must be positive")

        return errors

    def _validate_governance(self) -> List[str]:
        """Validate governance configuration."""
        errors = []

        enabled = self.get("governance.enabled")
        if not isinstance(enabled, bool):
            errors.append("governance.enabled must be a boolean")

        strategy = self.get("governance.coordination_strategy")
        if strategy not in ["consensus", "majority", "weighted_vote", "sequential"]:
            errors.append(
                "governance.coordination_strategy must be one of: "
                "consensus, majority, weighted_vote, sequential"
            )

        approval_threshold = self.get("governance.approval_threshold")
        if not isinstance(approval_threshold, (int, float)) or not 0 <= approval_threshold <= 1:
            errors.append("governance.approval_threshold must be in [0, 1]")

        return errors

    def _validate_logging(self) -> List[str]:
        """Validate logging configuration."""
        errors = []

        level = self.get("logging.level")
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if level not in valid_levels:
            errors.append(f"logging.level must be one of: {', '.join(valid_levels)}")

        console_format = self.get("logging.console.format")
        if console_format not in ["simple", "detailed", "json"]:
            errors.append("logging.console.format must be: simple, detailed, or json")

        max_size = self.get("logging.file.max_size_mb")
        if not isinstance(max_size, (int, float)) or max_size <= 0:
            errors.append("logging.file.max_size_mb must be a positive number")

        return errors

    def _deep_merge(self, base: Dict, override: Dict) -> Dict:
        """
        Deep merge two dictionaries.

        Args:
            base: Base dictionary
            override: Override dictionary

        Returns:
            Merged dictionary
        """
        result = copy.deepcopy(base)

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = copy.deepcopy(value)

        return result

    def _flatten_to_nested(self, flat_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert flat dictionary with dot notation to nested dictionary.

        Args:
            flat_dict: Dictionary with dot-notation keys

        Returns:
            Nested dictionary

        Example:
            >>> _flatten_to_nested({"a.b.c": 1, "a.b.d": 2})
            {"a": {"b": {"c": 1, "d": 2}}}
        """
        result = {}

        for key, value in flat_dict.items():
            parts = key.split('.')
            current = result

            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]

            current[parts[-1]] = value

        return result

    def save(self, path: str):
        """
        Save current configuration to YAML file.

        Args:
            path: Path to save configuration
        """
        try:
            with open(path, 'w') as f:
                yaml.dump(self.config, f, default_flow_style=False, sort_keys=False)
            logger.info(f"Saved configuration to {path}")
        except Exception as e:
            raise RuntimeError(f"Failed to save configuration: {e}")

    def to_dict(self) -> Dict[str, Any]:
        """
        Get configuration as dictionary.

        Returns:
            Configuration dictionary (deep copy)
        """
        return copy.deepcopy(self.config)

    def __repr__(self) -> str:
        """String representation."""
        return f"ConfigManager(sections={list(self.config.keys())})"

    def __str__(self) -> str:
        """Human-readable string."""
        return yaml.dump(self.config, default_flow_style=False)


# Convenience functions

def load_config(
    config_path: Optional[str] = None,
    config_override: Optional[Dict[str, Any]] = None
) -> ConfigManager:
    """
    Convenience function to load configuration.

    Args:
        config_path: Path to custom config file
        config_override: Dictionary of overrides

    Returns:
        ConfigManager instance
    """
    return ConfigManager(config_path=config_path, config_override=config_override)


def get_default_config() -> Dict[str, Any]:
    """
    Get default configuration as dictionary.

    Returns:
        Default configuration dictionary
    """
    config = ConfigManager()
    return config.to_dict()

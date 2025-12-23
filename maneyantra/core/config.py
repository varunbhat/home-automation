"""Configuration management."""

import os
import re
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from dotenv import load_dotenv


class ConfigManager:
    """
    Configuration manager for loading and managing system and plugin configs.

    Supports:
    - YAML configuration files
    - Environment variable interpolation (${VAR_NAME})
    - Default values
    """

    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.system_config: Dict[str, Any] = {}
        self.plugin_configs: Dict[str, Dict[str, Any]] = {}

        # Load environment variables
        load_dotenv()

    def load(self) -> None:
        """Load all configuration files."""
        self._load_system_config()
        self._load_plugin_configs()

    def _load_system_config(self) -> None:
        """Load system configuration."""
        config_path = self.config_dir / "system.yaml"

        if not config_path.exists():
            # Try example file
            example_path = self.config_dir / "system.yaml.example"
            if example_path.exists():
                config_path = example_path
            else:
                raise FileNotFoundError(f"System config not found: {config_path}")

        with open(config_path) as f:
            raw_config = yaml.safe_load(f)

        # Interpolate environment variables
        self.system_config = self._interpolate_env_vars(raw_config)

    def _load_plugin_configs(self) -> None:
        """Load plugin configurations."""
        config_path = self.config_dir / "plugins.yaml"

        if not config_path.exists():
            # Try example file
            example_path = self.config_dir / "plugins.yaml.example"
            if example_path.exists():
                config_path = example_path
            else:
                raise FileNotFoundError(f"Plugin config not found: {config_path}")

        with open(config_path) as f:
            raw_config = yaml.safe_load(f)

        plugins = raw_config.get("plugins", {})

        for plugin_id, plugin_config in plugins.items():
            # Interpolate environment variables
            self.plugin_configs[plugin_id] = self._interpolate_env_vars(plugin_config)

    def _interpolate_env_vars(self, config: Any) -> Any:
        """
        Recursively interpolate environment variables in config.

        Supports ${VAR_NAME} syntax.
        """
        if isinstance(config, dict):
            return {k: self._interpolate_env_vars(v) for k, v in config.items()}
        elif isinstance(config, list):
            return [self._interpolate_env_vars(item) for item in config]
        elif isinstance(config, str):
            return self._interpolate_string(config)
        else:
            return config

    @staticmethod
    def _interpolate_string(value: str) -> str:
        """Interpolate environment variables in a string."""
        pattern = re.compile(r'\$\{([^}]+)\}')

        def replacer(match):
            var_name = match.group(1)
            return os.getenv(var_name, match.group(0))

        return pattern.sub(replacer, value)

    def get_system_config(self) -> Dict[str, Any]:
        """Get system configuration."""
        return self.system_config

    def get_plugin_config(self, plugin_id: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific plugin."""
        return self.plugin_configs.get(plugin_id)

    def get_enabled_plugins(self) -> Dict[str, Dict[str, Any]]:
        """Get all enabled plugins."""
        return {
            plugin_id: config
            for plugin_id, config in self.plugin_configs.items()
            if config.get("enabled", False)
        }

    def get_rabbitmq_config(self) -> Dict[str, Any]:
        """Get RabbitMQ configuration."""
        rabbitmq_config = self.system_config.get("rabbitmq", {})

        if not rabbitmq_config:
            raise ValueError(
                "RabbitMQ configuration not found in config/system.yaml. "
                "Please add a 'rabbitmq' section with host, port, username, password, vhost, and exchange_name."
            )

        # Override with environment variables if present
        return {
            "host": os.getenv("RABBITMQ_HOST", rabbitmq_config.get("host", "localhost")),
            "port": int(os.getenv("RABBITMQ_PORT", rabbitmq_config.get("port", 5672))),
            "username": os.getenv("RABBITMQ_USERNAME", rabbitmq_config.get("username", "guest")),
            "password": os.getenv("RABBITMQ_PASSWORD", rabbitmq_config.get("password", "guest")),
            "vhost": os.getenv("RABBITMQ_VHOST", rabbitmq_config.get("vhost", "/")),
            "exchange_name": rabbitmq_config.get("exchange_name", "maneyantra"),
        }

    def get_log_level(self) -> str:
        """Get log level from config or environment."""
        return os.getenv(
            "LOG_LEVEL",
            self.system_config.get("system", {}).get("log_level", "INFO")
        )

    def get_paths(self) -> Dict[str, Path]:
        """Get configured paths."""
        paths = self.system_config.get("paths", {})

        return {
            "data": Path(os.getenv("DATA_DIR", paths.get("data", "./data"))),
            "logs": Path(os.getenv("LOGS_DIR", paths.get("logs", "./logs"))),
            "plugins": Path(paths.get("plugins", "./maneyantra/plugins")),
        }

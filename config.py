import os
import re
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class FeatureConfig:
    enabled: bool
    config: Dict[str, Any]

class BotConfig:
    def __init__(self, env_file: str = ".env"):
        self.env_file = env_file
        self.load_env_file()
        
        # Load plugin configuration
        self.plugin_config = self._load_plugin_config()
        
    def load_env_file(self):
        """Load environment variables from file"""
        if Path(self.env_file).exists():
            with open(self.env_file) as f:
                for line in f:
                    if '=' in line and not line.strip().startswith('#'):
                        key, value = line.strip().split('=', 1)
                        os.environ[key] = value
    
    def _load_plugin_config(self) -> Dict[str, Any]:
        """Load plugin configuration from YAML with environment variable interpolation"""
        config_file = Path("config/plugins.yaml")
        if config_file.exists():
            with open(config_file) as f:
                content = f.read()
                # Replace ${VAR_NAME} with environment variable values
                content = self._substitute_env_vars(content)
                return yaml.safe_load(content) or {}
        return {}
    
    def _substitute_env_vars(self, content: str) -> str:
        """Substitute ${VAR_NAME} patterns with environment variable values"""
        def replace_var(match):
            var_name = match.group(1)
            return os.getenv(var_name, match.group(0))  # Return original if env var not found
        
        # Match ${VAR_NAME} pattern
        pattern = r'\$\{([A-Z_][A-Z0-9_]*)\}'
        return re.sub(pattern, replace_var, content)
    
    def is_plugin_enabled(self, plugin_name: str) -> bool:
        """Check if plugin is enabled in config"""
        plugin_config = self.plugin_config.get(plugin_name, {})
        return plugin_config.get("enabled", False)
    
    def get_plugin_config(self, plugin_name: str) -> Dict[str, Any]:
        """Get configuration for specific plugin"""
        return self.plugin_config.get(plugin_name, {}).get("config", {})
    
    # Matrix config properties
    @property
    def homeserver(self):
        return os.getenv("HOMESERVER", "https://matrix.org")
    
    @property
    def user_id(self):
        return os.getenv("USER_ID")
    
    @property
    def password(self):
        return os.getenv("PASSWORD")
    
    @property
    def room_id(self):
        return os.getenv("ROOM_ID")
    
    @property
    def openrouter_key(self):
        return os.getenv("OPENROUTER_API_KEY")
    
    @property
    def database_api_key(self):
        return os.getenv("DATABASE_API_KEY")
    
    @property
    def database_api_url(self):
        return os.getenv("DATABASE_API_URL")
    
    # Legacy methods for backward compatibility
    def is_feature_enabled(self, feature_name: str) -> bool:
        return self.is_plugin_enabled(feature_name)
    
    def get_feature_config(self, feature_name: str) -> Dict[str, Any]:
        return self.get_plugin_config(feature_name)
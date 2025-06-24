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
            env_value = os.getenv(var_name)
            if env_value is None:
                return match.group(0)  # Return original if env var not found
            
            # Special handling for list variables (comma-separated)
            if var_name in ['ADMIN_USERS', 'ADMIN_ROOMS']:
                # Convert comma-separated string to JSON-style YAML list
                items = [item.strip() for item in env_value.split(',') if item.strip()]
                # Use JSON-style list format that's valid YAML (no outer quotes)
                return '[' + ', '.join(f'"{item}"' for item in items) + ']'
            
            return env_value
        
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
        return os.getenv("HOMESERVER") or os.getenv("MATRIX_HOMESERVER_URL")
    
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
    
    # Admin authorization methods
    def is_admin_user(self, user_id: str) -> bool:
        """Check if user is authorized for admin commands"""
        core_config = self.get_plugin_config("core")
        admin_users = core_config.get("admin_users", [])
        return user_id in admin_users
    
    def is_admin_room(self, room_id: str) -> bool:
        """Check if room allows admin commands"""
        core_config = self.get_plugin_config("core")
        admin_rooms = core_config.get("admin_rooms", [])
        return room_id in admin_rooms
    
    def are_config_commands_allowed(self) -> bool:
        """Check if config commands are globally enabled"""
        core_config = self.get_plugin_config("core")
        return core_config.get("allow_config_commands", False)
    
    def is_authorized_for_config(self, user_id: str, room_id: str) -> bool:
        """Check if user is authorized to run config commands in this room"""
        return (
            self.are_config_commands_allowed() and
            self.is_admin_user(user_id) and
            self.is_admin_room(room_id)
        )
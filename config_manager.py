"""
Dynamic Configuration Manager
Handles runtime configuration changes for plugins via chat commands
"""
import os
import re
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from config import BotConfig


class ConfigManager:
    """Manages dynamic configuration changes to plugins.yaml"""
    
    def __init__(self):
        self.config_file = Path("config/plugins.yaml")
        self.backup_file = Path("config/plugins.yaml.backup")
    
    def validate_plugin_setting(self, plugin_name: str, setting: str, value: str) -> Tuple[bool, str, Any]:
        """
        Validate a plugin setting change
        Returns: (is_valid, error_message, parsed_value)
        """
        # Security: Only allow alphanumeric plugin names
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', plugin_name):
            return False, "Invalid plugin name", None
        
        # Security: Only allow alphanumeric setting names with dots and underscores
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_\.]*$', setting):
            return False, "Invalid setting name", None
        
        # Parse value based on common patterns
        parsed_value = self._parse_config_value(value)
        
        # Plugin-specific validation
        validation_error = self._validate_plugin_specific(plugin_name, setting, parsed_value)
        if validation_error:
            return False, validation_error, None
        
        return True, "", parsed_value
    
    def _parse_config_value(self, value: str) -> Any:
        """Parse string value to appropriate type"""
        value = value.strip()
        
        # Boolean values
        if value.lower() in ['true', 'yes', 'on', 'enabled']:
            return True
        if value.lower() in ['false', 'no', 'off', 'disabled']:
            return False
        
        # Numeric values
        if value.isdigit():
            return int(value)
        
        try:
            return float(value)
        except ValueError:
            pass
        
        # String value (remove quotes if present)
        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
        elif value.startswith("'") and value.endswith("'"):
            value = value[1:-1]
        
        return value
    
    def _validate_plugin_specific(self, plugin_name: str, setting: str, value: Any) -> Optional[str]:
        """Plugin-specific validation rules"""
        
        if plugin_name == "ai":
            if setting == "temperature" and isinstance(value, (int, float)):
                if not 0.0 <= value <= 2.0:
                    return "temperature must be between 0.0 and 2.0"
            elif setting == "max_tokens" and isinstance(value, int):
                if not 1 <= value <= 10000:
                    return "max_tokens must be between 1 and 10000"
            elif setting == "model" and not isinstance(value, str):
                return "model must be a string"
        
        elif plugin_name == "youtube":
            if setting == "max_cached_per_room" and isinstance(value, int):
                if not 1 <= value <= 100:
                    return "max_cached_per_room must be between 1 and 100"
            elif setting == "chunk_size" and isinstance(value, int):
                if not 1000 <= value <= 50000:
                    return "chunk_size must be between 1000 and 50000"
        
        elif plugin_name == "database":
            if setting == "timeout" and isinstance(value, int):
                if not 5 <= value <= 300:
                    return "timeout must be between 5 and 300 seconds"
            elif setting in ["api_url", "api_key"]:
                return "api_url and api_key cannot be changed via chat commands for security"
        
        elif plugin_name == "core":
            if setting in ["admin_users", "admin_rooms", "allow_config_commands"]:
                return "core security settings cannot be changed via chat commands"
        
        return None
    
    def get_plugin_setting(self, plugin_name: str, setting: str) -> Tuple[bool, str, Any]:
        """Get current value of a plugin setting"""
        try:
            config = BotConfig()
            plugin_config = config.get_plugin_config(plugin_name)
            
            if not plugin_config:
                return False, f"Plugin '{plugin_name}' not found", None
            
            # Support nested settings like "config.enabled"
            value = plugin_config
            for part in setting.split('.'):
                if isinstance(value, dict) and part in value:
                    value = value[part]
                else:
                    return False, f"Setting '{setting}' not found in plugin '{plugin_name}'", None
            
            return True, "", value
            
        except Exception as e:
            return False, f"Error reading setting: {e}", None
    
    def set_plugin_setting(self, plugin_name: str, setting: str, value: Any) -> Tuple[bool, str]:
        """Set a plugin setting in plugins.yaml"""
        try:
            # Read current YAML content (raw, before env var substitution)
            if not self.config_file.exists():
                return False, "plugins.yaml not found"
            
            with open(self.config_file, 'r') as f:
                content = f.read()
            
            # Create backup
            with open(self.backup_file, 'w') as f:
                f.write(content)
            
            # Parse YAML
            data = yaml.safe_load(content)
            
            # Ensure plugin exists
            if plugin_name not in data:
                data[plugin_name] = {"enabled": True, "config": {}}
            if "config" not in data[plugin_name]:
                data[plugin_name]["config"] = {}
            
            # Set the value (support nested settings)
            config_section = data[plugin_name]["config"]
            setting_parts = setting.split('.')
            
            # Navigate to the right nested location
            for part in setting_parts[:-1]:
                if part not in config_section:
                    config_section[part] = {}
                config_section = config_section[part]
            
            # Set the final value
            config_section[setting_parts[-1]] = value
            
            # Write back to file
            with open(self.config_file, 'w') as f:
                yaml.dump(data, f, default_flow_style=False, sort_keys=False)
            
            return True, ""
            
        except Exception as e:
            # Restore backup on error
            if self.backup_file.exists():
                with open(self.backup_file, 'r') as f:
                    backup_content = f.read()
                with open(self.config_file, 'w') as f:
                    f.write(backup_content)
            
            return False, f"Error updating config: {e}"
    
    def list_plugin_settings(self, plugin_name: str) -> Tuple[bool, str, Dict[str, Any]]:
        """List all settings for a plugin"""
        try:
            config = BotConfig()
            plugin_config = config.get_plugin_config(plugin_name)
            
            if not plugin_config:
                return False, f"Plugin '{plugin_name}' not found", {}
            
            return True, "", plugin_config
            
        except Exception as e:
            return False, f"Error reading plugin config: {e}", {}
    
    def cleanup_backup(self):
        """Remove backup file after successful operation"""
        if self.backup_file.exists():
            self.backup_file.unlink()
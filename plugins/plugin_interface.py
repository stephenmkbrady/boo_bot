from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any

class BotPlugin(ABC):
    """Base interface that all plugins must implement"""
    
    def __init__(self, name: str):
        self.name = name
        self.enabled = True
        self.version = "1.0.0"
        self.description = "A bot plugin"
        
    @abstractmethod
    def get_commands(self) -> List[str]:
        """Return list of commands this plugin handles"""
        pass
    
    @abstractmethod
    async def handle_command(self, command: str, args: str, room_id: str, user_id: str, bot_instance) -> Optional[str]:
        """Handle a command and return response or None"""
        pass
    
    async def initialize(self, bot_instance) -> bool:
        """Initialize plugin with bot instance. Return True if successful."""
        return True
    
    async def cleanup(self):
        """Cleanup when plugin is disabled/unloaded"""
        pass
    
    def can_handle(self, command: str) -> bool:
        """Check if this plugin can handle the command"""
        return command in self.get_commands()
    
    def get_info(self) -> Dict[str, Any]:
        """Return plugin information"""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "enabled": self.enabled,
            "commands": self.get_commands()
        }
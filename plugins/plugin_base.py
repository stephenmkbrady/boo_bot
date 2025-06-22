from abc import ABC, abstractmethod
from typing import List, Optional


class BotPlugin(ABC):
    def __init__(self, name: str):
        self.name = name
        self.enabled = True
    
    @abstractmethod
    def get_commands(self) -> List[str]:
        """Return commands this plugin handles"""
        pass
    
    @abstractmethod
    async def handle_command(self, command: str, args: str, room_id: str, user_id: str) -> Optional[str]:
        """Handle a command, return response or None"""
        pass
    
    def can_handle(self, command: str) -> bool:
        """Check if this plugin can handle the command"""
        return command in self.get_commands()
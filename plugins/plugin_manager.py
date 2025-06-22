from typing import List, Optional, Dict
from .plugin_base import BotPlugin


class PluginManager:
    def __init__(self):
        self.plugins: List[BotPlugin] = []
    
    def add_plugin(self, plugin: BotPlugin):
        self.plugins.append(plugin)
    
    def remove_plugin(self, plugin_name: str):
        self.plugins = [p for p in self.plugins if p.name != plugin_name]
    
    async def handle_command(self, command: str, args: str, room_id: str, user_id: str) -> Optional[str]:
        for plugin in self.plugins:
            if plugin.enabled and plugin.can_handle(command):
                return await plugin.handle_command(command, args, room_id, user_id)
        return None
    
    def get_all_commands(self) -> Dict[str, str]:
        commands = {}
        for plugin in self.plugins:
            if plugin.enabled:
                for cmd in plugin.get_commands():
                    commands[cmd] = plugin.name
        return commands
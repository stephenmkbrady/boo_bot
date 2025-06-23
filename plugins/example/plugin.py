"""
Example Plugin - Skeleton/Template for Creating New Plugins

This plugin is disabled by default and serves as a reference for creating new plugins.
It demonstrates the basic plugin structure and implements a simple echo command.

To enable this plugin:
1. Set enabled: true in config/plugins.yaml, OR
2. Set self.enabled = True in __init__, OR  
3. Use the bot command: bot: enable example

To create a new plugin based on this example:
1. Copy this entire plugins/example/ folder
2. Rename the folder to your plugin name (e.g., plugins/myfeature/)
3. Modify the plugin class name and functionality
4. Update the commands and descriptions
5. Add your plugin to config/plugins.yaml
"""

from typing import List, Optional
import logging
from plugins.plugin_interface import BotPlugin


class ExamplePlugin(BotPlugin):
    def __init__(self):
        super().__init__("example")
        self.version = "1.0.0"
        self.description = "Example skeleton plugin that echoes user messages"
        
        # IMPORTANT: This plugin is disabled by default for safety
        # Set to True to enable this plugin
        self.enabled = False
        
        self.logger = logging.getLogger(f"plugin.{self.name}")
    
    async def initialize(self, bot_instance) -> bool:
        """Initialize the plugin with bot instance"""
        try:
            self.bot = bot_instance
            
            # Load configuration from config/plugins.yaml
            try:
                from config import BotConfig
                config = BotConfig()
                
                # Check if plugin is enabled in config file
                config_enabled = config.is_plugin_enabled(self.name)
                self.enabled = config_enabled
                
                # Load plugin-specific configuration
                plugin_config = config.get_plugin_config(self.name)
                self.demo_mode = plugin_config.get("demo_mode", True)
                self.max_echo_length = plugin_config.get("max_echo_length", 1000)
                
                self.logger.info(f"Loaded config: demo_mode={self.demo_mode}, max_echo_length={self.max_echo_length}")
                
            except ImportError:
                self.logger.warning("Config system not available, using defaults")
                self.demo_mode = True
                self.max_echo_length = 1000
            
            if not self.enabled:
                self.logger.info("Example plugin is disabled (enable in config/plugins.yaml or use 'bot: enable example')")
                return True
            
            self.logger.info("Example plugin initialized successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize example plugin: {e}")
            return False
    
    def get_commands(self) -> List[str]:
        """Return list of commands this plugin handles"""
        return ["echo", "repeat", "example"]
    
    async def handle_command(self, command: str, args: str, room_id: str, user_id: str, bot_instance) -> Optional[str]:
        """Handle commands for this plugin"""
        self.logger.info(f"Handling {command} command from {user_id} in {room_id}")
        
        if not self.enabled:
            return "❌ Example plugin is disabled. Enable it in plugins/example/plugin.py"
        
        try:
            if command == "echo":
                return await self._handle_echo(args, user_id)
            elif command == "repeat":
                return await self._handle_repeat(args, user_id)
            elif command == "example":
                return await self._handle_example(args, user_id)
        except Exception as e:
            self.logger.error(f"Error handling {command} command from {user_id}: {str(e)}", exc_info=True)
            return f"❌ Error processing {command} command"
        
        return None
    
    async def _handle_echo(self, args: str, user_id: str) -> str:
        """Echo back the user's message"""
        if not args:
            return "🔊 **Echo Command**\n\nUsage: `echo <message>`\nI'll repeat whatever you type!"
        
        # Respect max_echo_length configuration
        if len(args) > self.max_echo_length:
            args = args[:self.max_echo_length] + "... (truncated)"
        
        # Add demo mode information if enabled
        demo_info = "\n🎯 *Demo mode active - this is a template plugin!*" if self.demo_mode else ""
        
        return f"🔊 **Echo from {user_id}:**\n{args}{demo_info}"
    
    async def _handle_repeat(self, args: str, user_id: str) -> str:
        """Repeat the user's message multiple times"""
        if not args:
            return "🔁 **Repeat Command**\n\nUsage: `repeat <message>`\nI'll repeat your message 3 times!"
        
        # Repeat the message 3 times
        repeated = "\n".join([f"{i+1}. {args}" for i in range(3)])
        return f"🔁 **Repeating message from {user_id}:**\n{repeated}"
    
    async def _handle_example(self, args: str, user_id: str) -> str:
        """Show example of plugin capabilities"""
        return f"""🎯 **Example Plugin Demo**

**Available Commands:**
• `echo <message>` - Echo back your message
• `repeat <message>` - Repeat your message 3 times  
• `example` - Show this demo

**Plugin Info:**
• Name: {self.name}
• Version: {self.version}
• Enabled: {self.enabled}
• User: {user_id}

**Configuration:**
• Demo Mode: {self.demo_mode}
• Max Echo Length: {self.max_echo_length}

**Arguments received:** {args if args else "(none)"}

This is a skeleton plugin for developers to use as a template! 🚀"""
    
    async def cleanup(self):
        """Cleanup when plugin is unloaded"""
        self.logger.info("Example plugin cleanup completed")


# This is the class that will be automatically discovered and loaded
# The plugin manager looks for classes that inherit from BotPlugin
# Make sure your main plugin class is defined in this file!
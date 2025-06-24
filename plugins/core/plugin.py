from typing import List, Optional
import logging
from plugins.plugin_interface import BotPlugin
from config import BotConfig
from config_manager import ConfigManager


class CorePlugin(BotPlugin):
    def __init__(self):
        super().__init__("core")
        self.version = "1.0.0"
        self.description = "Core bot commands (help, debug, ping, plugin management) - HOT RELOAD TEST"
        self.logger = logging.getLogger(f"plugin.{self.name}")
        self.bot = None
    
    async def initialize(self, bot_instance) -> bool:
        """Initialize plugin with bot instance"""
        self.bot = bot_instance
        self.config_manager = ConfigManager()
        self.logger.info("Core plugin initialized successfully")
        return True
    
    def get_commands(self) -> List[str]:
        return ["debug", "talk", "help", "ping", "room", "refresh", "update", "name", "status", "plugins", "reload", "enable", "disable", "config"]
    
    async def handle_command(self, command: str, args: str, room_id: str, user_id: str, bot_instance) -> Optional[str]:
        self.logger.info(f"Handling {command} command from {user_id} in {room_id}")
        
        if not self.bot:
            self.logger.error("Bot instance not available")
            return "❌ Bot instance not available"
        
        try:
            if command == "debug":
                return await self._handle_debug_command(bot_instance)
            elif command == "talk":
                return "Hello! 👋 I'm your friendly Matrix bot. How can I help you today?"
            elif command == "help":
                return await self._handle_help_command(bot_instance)
            elif command == "ping":
                return "Pong! 🏓"
            elif command == "status":
                return await self._handle_status(bot_instance)
            elif command == "plugins":
                return await self._handle_plugins(bot_instance)
            elif command == "reload":
                return await self._handle_reload(args, bot_instance)
            elif command == "enable":
                return await self._handle_enable(args, bot_instance)
            elif command == "disable":
                return await self._handle_disable(args, bot_instance)
            elif command == "config":
                return await self._handle_config(args, room_id, user_id, bot_instance)
            elif command == "room":
                return await self._handle_room_command(room_id, bot_instance)
            elif command in ["refresh", "update"] and args == "name":
                return await self._handle_refresh_name_command(bot_instance)
            elif command == "name" and args in ["refresh", "update"]:
                return await self._handle_refresh_name_command(bot_instance)
        except Exception as e:
            self.logger.error(f"Error handling {command} command from {user_id}: {str(e)}", exc_info=True)
            return f"❌ Error processing {command} command"
        
        return None
    
    async def _handle_debug_command(self, bot_instance) -> str:
        """Handle debug command"""
        return f"""🔍 **DEBUG INFO**

📊 **Event Counters:**
• Text: {bot_instance.event_counters['text_messages']}
• Media: {bot_instance.event_counters['media_messages']}
• Encrypted: {bot_instance.event_counters['encrypted_events']}
• Decrypt fails: {bot_instance.event_counters['decryption_failures']}

🤖 **Bot Info:**
• Display name: {bot_instance.current_display_name}
• User ID: {bot_instance.user_id}
• Store path: {bot_instance.store_path}"""
    
    async def _handle_help_command(self, bot_instance) -> str:
        """Handle help command"""
        if not bot_instance.plugin_manager:
            return "❌ Plugin system not available"
        
        commands = bot_instance.plugin_manager.get_all_commands()
        help_text = f"🤖 **{bot_instance.current_display_name} Commands:**\n\n"
        
        # Group commands by plugin
        by_plugin = {}
        for cmd, plugin_name in commands.items():
            if plugin_name not in by_plugin:
                by_plugin[plugin_name] = []
            by_plugin[plugin_name].append(cmd)
        
        for plugin_name, cmds in by_plugin.items():
            help_text += f"**{plugin_name.title()}:** {', '.join(cmds)}\n"
        
        return help_text
    
    async def _handle_status(self, bot_instance) -> str:
        if not bot_instance.plugin_manager:
            return "❌ Plugin system not available"
        
        status = bot_instance.plugin_manager.get_plugin_status()
        hot_reload_status = "🔥 Active" if status.get('hot_reloading') else "❄️ Inactive"
        
        return f"""📊 **Bot Status**

🔌 **Plugins:** {status['total_loaded']} loaded, {status['total_failed']} failed
🔥 **Hot Reloading:** {hot_reload_status}
📨 **Messages processed:** {bot_instance.event_counters['text_messages']}
🔐 **Encryption:** {'✅ Active' if bot_instance.client.olm else '❌ Disabled'}"""
    
    async def _handle_plugins(self, bot_instance) -> str:
        if not bot_instance.plugin_manager:
            return "❌ Plugin system not available"
        
        status = bot_instance.plugin_manager.get_plugin_status()
        response = "🔌 **Plugin Status:**\n\n"
        
        for name, info in status['loaded'].items():
            enabled_emoji = "✅" if info['enabled'] else "❌"
            response += f"{enabled_emoji} **{info['name']}** v{info['version']}\n"
            response += f"   {info['description']}\n"
            response += f"   Commands: {', '.join(info['commands'])}\n\n"
        
        if status['failed']:
            response += "❌ **Failed Plugins:**\n"
            for name, error in status['failed'].items():
                response += f"• {name}: {error}\n"
        
        hot_reload_status = "🔥 Active" if status.get('hot_reloading') else "❄️ Inactive"
        response += f"\n🔥 **Hot Reloading:** {hot_reload_status}"
        
        return response
    
    async def _handle_reload(self, args: str, bot_instance) -> str:
        if not bot_instance.plugin_manager:
            return "❌ Plugin system not available"
        
        if not args:
            return "❌ Please specify a plugin name to reload. Example: `reload youtube`"
        
        plugin_name = args.strip()
        success = await bot_instance.plugin_manager.reload_plugin(plugin_name)
        
        if success:
            return f"✅ Plugin `{plugin_name}` reloaded successfully"
        else:
            return f"❌ Failed to reload plugin `{plugin_name}`"
    
    async def _handle_enable(self, args: str, bot_instance) -> str:
        if not bot_instance.plugin_manager:
            return "❌ Plugin system not available"
        
        if not args:
            return "❌ Please specify a plugin name to enable. Example: `enable youtube`"
        
        plugin_name = args.strip()
        success = bot_instance.plugin_manager.enable_plugin(plugin_name)
        
        if success:
            return f"✅ Plugin `{plugin_name}` enabled"
        else:
            return f"❌ Plugin `{plugin_name}` not found"
    
    async def _handle_disable(self, args: str, bot_instance) -> str:
        if not bot_instance.plugin_manager:
            return "❌ Plugin system not available"
        
        if not args:
            return "❌ Please specify a plugin name to disable. Example: `disable youtube`"
        
        plugin_name = args.strip()
        success = bot_instance.plugin_manager.disable_plugin(plugin_name)
        
        if success:
            return f"⏸️ Plugin `{plugin_name}` disabled"
        else:
            return f"❌ Plugin `{plugin_name}` not found"
    
    async def _handle_room_command(self, room_id: str, bot_instance) -> str:
        """Handle room command"""
        try:
            room = bot_instance.client.rooms.get(room_id)
            if not room:
                return "❌ Room information not available"
            
            room_info = f"""🏠 ROOM INFO:
Name: {room.name or 'Unnamed Room'}
ID: {room.room_id}
Members: {len(room.users)}
Encrypted: {'✅' if room.encrypted else '❌'}
Power Level: {room.power_levels.get(bot_instance.user_id, 0)}"""
            
            return room_info
        except Exception as e:
            return f"❌ Error getting room info: {str(e)}"
    
    async def _handle_refresh_name_command(self, bot_instance) -> str:
        """Handle refresh name command"""
        try:
            if hasattr(bot_instance, 'update_command_prefix'):
                await bot_instance.update_command_prefix()
                return f"✅ Display name refreshed: {getattr(bot_instance, 'current_display_name', 'Unknown')}"
            else:
                return "❌ Name refresh not available"
        except Exception as e:
            return f"❌ Error refreshing name: {str(e)}"
    
    async def _handle_config(self, args: str, room_id: str, user_id: str, bot_instance) -> str:
        """Handle config command with authorization"""
        if not bot_instance.plugin_manager:
            return "❌ Plugin manager not available"
        
        # Check authorization for config commands
        config = BotConfig()
        if not config.is_authorized_for_config(user_id, room_id):
            return "❌ You are not authorized to use config commands in this room"
        
        args = args.strip()
        if not args:
            return self._get_config_help()
        
        parts = args.split()
        subcommand = parts[0].lower()
        
        if subcommand == "reload":
            return await self._handle_config_reload(bot_instance)
        elif subcommand == "list":
            return await self._handle_config_list(parts[1:])
        elif subcommand == "get":
            return await self._handle_config_get(parts[1:])
        elif subcommand == "set":
            return await self._handle_config_set(parts[1:], bot_instance)
        else:
            return f"❌ Unknown config command '{subcommand}'. Use `config` for help."
    
    def _get_config_help(self) -> str:
        """Get configuration help text"""
        return """⚙️ **Configuration Commands:**

**General:**
• `config` - Show this help
• `config reload` - Reload plugins.yaml and restart all plugins

**Plugin Configuration:**
• `config list <plugin>` - Show all settings for a plugin
• `config get <plugin> <setting>` - Get current value of a setting
• `config set <plugin> <setting> <value>` - Set a plugin setting

**Examples:**
• `config list ai` - Show all AI plugin settings
• `config get ai model` - Get current AI model
• `config set ai model "new-model-name"` - Set AI model
• `config set ai temperature 0.7` - Set AI temperature
• `config set youtube max_cached_per_room 10` - Set YouTube cache limit

**Security:** Only authorized users in authorized rooms can use config commands.
**Note:** Settings are automatically validated and applied with hot reloading."""
    
    async def _handle_config_reload(self, bot_instance) -> str:
        """Handle config reload command"""
        try:
            await bot_instance.plugin_manager._handle_config_change()
            self.config_manager.cleanup_backup()
            return "✅ Configuration reloaded - all plugins restarted with new config"
        except Exception as e:
            return f"❌ Error reloading configuration: {str(e)}"
    
    async def _handle_config_list(self, args: List[str]) -> str:
        """Handle config list command"""
        if len(args) != 1:
            return "❌ Usage: `config list <plugin>`"
        
        plugin_name = args[0].lower()
        success, error, settings = self.config_manager.list_plugin_settings(plugin_name)
        
        if not success:
            return f"❌ {error}"
        
        if not settings:
            return f"📋 Plugin '{plugin_name}' has no settings configured"
        
        result = [f"📋 **{plugin_name.title()} Plugin Settings:**\n"]
        for key, value in settings.items():
            if isinstance(value, str) and len(str(value)) > 50:
                value = str(value)[:47] + "..."
            result.append(f"• `{key}`: {value}")
        
        return "\n".join(result)
    
    async def _handle_config_get(self, args: List[str]) -> str:
        """Handle config get command"""
        if len(args) != 2:
            return "❌ Usage: `config get <plugin> <setting>`"
        
        plugin_name, setting = args[0].lower(), args[1]
        success, error, value = self.config_manager.get_plugin_setting(plugin_name, setting)
        
        if not success:
            return f"❌ {error}"
        
        return f"⚙️ `{plugin_name}.{setting}` = `{value}`"
    
    async def _handle_config_set(self, args: List[str], bot_instance) -> str:
        """Handle config set command"""
        if len(args) < 3:
            return "❌ Usage: `config set <plugin> <setting> <value>`"
        
        plugin_name = args[0].lower()
        setting = args[1]
        value = " ".join(args[2:])  # Join remaining parts as value
        
        # Validate the setting change
        is_valid, error, parsed_value = self.config_manager.validate_plugin_setting(plugin_name, setting, value)
        if not is_valid:
            return f"❌ {error}"
        
        # Apply the setting
        success, error = self.config_manager.set_plugin_setting(plugin_name, setting, parsed_value)
        if not success:
            return f"❌ {error}"
        
        # Trigger hot reload
        try:
            await bot_instance.plugin_manager._handle_config_change()
            self.config_manager.cleanup_backup()
            return f"✅ Set `{plugin_name}.{setting}` = `{parsed_value}` (plugins reloaded)"
        except Exception as e:
            return f"⚠️ Setting updated but reload failed: {str(e)}"
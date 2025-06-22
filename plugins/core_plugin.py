from typing import List, Optional
import logging
from .plugin_base import BotPlugin


class CorePlugin(BotPlugin):
    def __init__(self, bot_instance=None):
        super().__init__("core")
        self.bot = bot_instance
        self.logger = logging.getLogger(f"plugin.{self.name}")
    
    def get_commands(self) -> List[str]:
        return ["debug", "talk", "help", "ping", "room", "refresh", "update", "name"]
    
    async def handle_command(self, command: str, args: str, room_id: str, user_id: str) -> Optional[str]:
        self.logger.info(f"Handling {command} command from {user_id} in {room_id}")
        
        if not self.bot:
            self.logger.error("Bot instance not available")
            return "❌ Bot instance not available"
        
        try:
            if command == "debug":
                return await self._handle_debug_command()
            elif command == "talk":
                return "Hello! 👋 I'm your friendly Matrix bot. How can I help you today?"
            elif command == "help":
                return await self._handle_help_command()
            elif command == "ping":
                return "Pong! 🏓"
            elif command == "room":
                return await self._handle_room_command(room_id)
            elif command in ["refresh", "update"] and args == "name":
                return await self._handle_refresh_name_command()
            elif command == "name" and args in ["refresh", "update"]:
                return await self._handle_refresh_name_command()
        except Exception as e:
            self.logger.error(f"Error handling {command} command from {user_id}: {str(e)}", exc_info=True)
            return f"❌ Error processing {command} command"
        
        return None
    
    async def _handle_debug_command(self) -> str:
        """Handle debug command"""
        if not hasattr(self.bot, 'event_counters'):
            return "Debug info not available"
        
        config_status = "✅ Enabled" if self.bot.config else "❌ Disabled"
        
        debug_info = f"""🐛 DEBUG INFO:
📊 Event Counters:
  Text Messages: {self.bot.event_counters.get('text_messages', 0)}
  Media Messages: {self.bot.event_counters.get('media_messages', 0)}
  Unknown Events: {self.bot.event_counters.get('unknown_events', 0)}
  Encrypted Events: {self.bot.event_counters.get('encrypted_events', 0)}
  Decryption Failures: {self.bot.event_counters.get('decryption_failures', 0)}

🤖 Bot Identity:
  User ID: {self.bot.user_id}
  Display Name: {getattr(self.bot, 'current_display_name', 'Unknown')}
  Device: {self.bot.device_name}

⚙️ Configuration: {config_status}
🎬 YouTube: {'✅' if self.bot.youtube_processor else '❌'}
🤖 AI: {'✅' if self.bot.ai_processor else '❌'}
📁 Media: {'✅' if self.bot.media_processor else '❌'}
💾 Database: {'✅' if getattr(self.bot, 'db_enabled', False) else '❌'}"""
        
        return debug_info
    
    async def _handle_help_command(self) -> str:
        """Handle help command"""
        help_text = """🤖 **BOO BOT HELP** 🤖

**Core Commands:**
• `debug` - Show debug information
• `talk` - Say hello
• `ping` - Test bot responsiveness
• `room` - Show room information
• `refresh name` - Update bot display name

**YouTube Commands:**
• `summary <url>` - Get video summary
• `subs <url>` - Extract captions
• `ask <url> <question>` - Ask about video
• `videos` - List recent videos

**AI Commands:**
• `8 [question]` - Magic 8-ball
• `advice <question>` - Get advice
• `bible` - Random Bible verse
• `song` - Bible verse + song

**Database Commands:**
• `db health` - Check database
• `db stats` - Database statistics

Use commands with the bot's name or mention."""
        
        return help_text
    
    async def _handle_room_command(self, room_id: str) -> str:
        """Handle room command"""
        try:
            room = self.bot.client.rooms.get(room_id)
            if not room:
                return "❌ Room information not available"
            
            room_info = f"""🏠 ROOM INFO:
Name: {room.name or 'Unnamed Room'}
ID: {room.room_id}
Members: {len(room.users)}
Encrypted: {'✅' if room.encrypted else '❌'}
Power Level: {room.power_levels.get(self.bot.user_id, 0)}"""
            
            return room_info
        except Exception as e:
            return f"❌ Error getting room info: {str(e)}"
    
    async def _handle_refresh_name_command(self) -> str:
        """Handle refresh name command"""
        try:
            if hasattr(self.bot, 'update_display_name'):
                await self.bot.update_display_name()
                return f"✅ Display name refreshed: {getattr(self.bot, 'current_display_name', 'Unknown')}"
            else:
                return "❌ Name refresh not available"
        except Exception as e:
            return f"❌ Error refreshing name: {str(e)}"
from typing import List, Optional
from plugin_base import BotPlugin


class DatabasePlugin(BotPlugin):
    def __init__(self, bot_instance=None):
        super().__init__("database")
        self.bot = bot_instance
        # Only enable if database is available
        self.enabled = bot_instance and getattr(bot_instance, 'db_enabled', False)
    
    def get_commands(self) -> List[str]:
        return ["db"]
    
    async def handle_command(self, command: str, args: str, room_id: str, user_id: str) -> Optional[str]:
        if not self.bot or not self.enabled:
            return "❌ Database functionality not available"
        
        try:
            if command == "db":
                if args == "health":
                    return await self._handle_db_health()
                elif args == "stats":
                    return await self._handle_db_stats()
                else:
                    return "❌ Unknown database command. Use 'db health' or 'db stats'"
        except Exception as e:
            return f"❌ Error processing database command: {str(e)}"
        
        return None
    
    async def _handle_db_health(self) -> str:
        """Handle database health check"""
        try:
            if not self.bot.db_client:
                return "❌ Database client not available"
            
            # health_check returns a boolean, not a dict
            is_healthy = await self.bot.db_client.health_check()
            
            if is_healthy:
                return "✅ Database is healthy!"
            else:
                return "❌ Database is unhealthy"
                
        except Exception as e:
            return f"❌ Database health check failed: {str(e)}"
    
    async def _handle_db_stats(self) -> str:
        """Handle database statistics"""
        try:
            if not self.bot.db_client:
                return "❌ Database client not available"
            
            stats = await self.bot.db_client.get_database_stats()
            
            if stats:
                total_messages = stats.get('total_messages', 'Unknown')
                total_media_files = stats.get('total_media_files', 'Unknown')
                database_size = stats.get('database_size', 'Unknown')
                
                return f"""📊 **DATABASE STATISTICS**
💬 Total Messages: {total_messages}
📎 Total Media Files: {total_media_files}
💾 Database Size: {database_size}"""
            else:
                return "❌ Could not retrieve database statistics"
                
        except Exception as e:
            return f"❌ Database stats failed: {str(e)}"
from typing import List, Optional
import logging
import asyncio
import aiohttp
import json
import os
from datetime import datetime
from plugins.plugin_interface import BotPlugin
from config import BotConfig


class AuthPlugin(BotPlugin):
    """Authentication plugin for PIN-based database access"""
    
    def __init__(self):
        super().__init__("auth")
        self.version = "1.0.0"
        self.description = "PIN authentication for database access - Request PINs for rooms"
        self.logger = logging.getLogger(f"plugin.{self.name}")
        self.bot = None
        self.api_base_url = None
        self.api_key = None
    
    async def initialize(self, bot_instance) -> bool:
        """Initialize plugin with bot instance and API configuration"""
        self.bot = bot_instance
        
        # Get API configuration from environment (use existing boo_bot env vars)
        self.api_base_url = os.getenv("DATABASE_API_URL", os.getenv("DATABASE_URL", "http://localhost:8000")).rstrip('/')
        self.api_key = os.getenv("DATABASE_API_KEY", os.getenv("API_KEY"))
        
        if not self.api_key:
            self.logger.error("API_KEY not found in environment variables")
            return False
        
        self.logger.info(f"Auth plugin initialized - API: {self.api_base_url}")
        return True
    
    def get_commands(self) -> List[str]:
        """Return list of commands this plugin handles"""
        return ["pin", "getpin"]
    
    async def handle_command(self, command: str, args: str, room_id: str, user_id: str, bot_instance) -> Optional[str]:
        """Handle authentication commands"""
        self.logger.info(f"Handling {command} command from {user_id} in room {room_id[:20]}...")
        
        if not self.bot:
            self.logger.error("Bot instance not available")
            return "❌ Bot instance not available"
        
        if not self.api_key:
            self.logger.error("API key not configured")
            return "❌ Authentication not configured properly"
        
        try:
            if command in ["pin", "getpin"]:
                return await self._handle_pin_request(room_id, user_id)
            else:
                return f"❌ Unknown auth command: {command}"
                
        except Exception as e:
            self.logger.error(f"Error handling {command}: {e}")
            return f"❌ Failed to process {command} command: {str(e)}"
    
    async def _handle_pin_request(self, room_id: str, user_id: str) -> str:
        """Request a PIN for the current room from boo_memories API"""
        try:
            url = f"{self.api_base_url}/rooms/{room_id}/pin"
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            self.logger.info(f"Requesting PIN for room {room_id[:20]}... from {url}")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        pin = data.get('pin')
                        expires_at = data.get('expires_at')
                        
                        # Parse expiration time for user-friendly display
                        try:
                            exp_dt = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                            exp_str = exp_dt.strftime('%H:%M UTC')
                        except:
                            exp_str = "24 hours"
                        
                        self.logger.info(f"✅ PIN generated successfully for room {room_id[:20]}...")
                        
                        return (
                            f"🔐 **Room Access PIN**: `{pin}`\\n\\n"
                            f"📝 Use this PIN in the web interface to access messages from this room.\\n"
                            f"⏰ **Expires**: {exp_str}\\n"
                            f"🔄 **Rate limit**: 3 requests per hour per room\\n\\n"
                            f"💡 Enter this PIN when prompted in the web dashboard to view room messages."
                        )
                    
                    elif response.status == 429:
                        self.logger.warning(f"Rate limit exceeded for room {room_id[:20]}...")
                        return (
                            f"⏱️ **Rate limit exceeded**\\n\\n"
                            f"This room has reached the maximum of 3 PIN requests per hour.\\n"
                            f"Please wait and try again later, or use the existing PIN if it hasn't expired."
                        )
                    
                    elif response.status == 503:
                        return (
                            f"🚫 **PIN authentication is currently disabled**\\n\\n"
                            f"Please contact the administrator."
                        )
                    
                    elif response.status == 401:
                        self.logger.error("API authentication failed - invalid API key")
                        return (
                            f"❌ **Authentication failed**\\n\\n"
                            f"Bot is not properly configured for PIN requests. Please contact the administrator."
                        )
                    
                    else:
                        error_text = await response.text()
                        self.logger.error(f"PIN request failed: {response.status} - {error_text}")
                        return (
                            f"❌ **PIN request failed**\\n\\n"
                            f"Server responded with error {response.status}. Please try again later."
                        )
                        
        except asyncio.TimeoutError:
            self.logger.error("PIN request timed out")
            return (
                f"⏰ **Request timed out**\\n\\n"
                f"The database server is not responding. Please try again later."
            )
            
        except aiohttp.ClientError as e:
            self.logger.error(f"Network error during PIN request: {e}")
            return (
                f"🌐 **Network error**\\n\\n"
                f"Could not connect to database server. Please try again later."
            )
            
        except Exception as e:
            self.logger.error(f"Unexpected error during PIN request: {e}")
            return (
                f"❌ **Unexpected error**\\n\\n"
                f"Failed to process PIN request: {str(e)}"
            )
    
    async def cleanup(self):
        """Cleanup when plugin is disabled/unloaded"""
        self.logger.info("Auth plugin cleanup completed")
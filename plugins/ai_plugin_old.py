from typing import List, Optional
import logging
import os
import aiohttp
import time
from .plugin_base import BotPlugin

AI_HANDLER_AVAILABLE = True  # Always available since we're embedding it


class AIProcessor:
    """Class to handle AI-powered content generation and NIST Beacon integration"""
    
    def __init__(self):
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        self.nist_beacon_url = "https://beacon.nist.gov/beacon/2.0/pulse/last"
        self.openrouter_url = "https://openrouter.ai/api/v1/chat/completions"
        self.model = "cognitivecomputations/dolphin3.0-mistral-24b:free"

    async def get_nist_beacon_random_number(self):
        """Get current NIST Randomness Beacon value and return as integer"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.nist_beacon_url,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:

                    if response.status == 200:
                        data = await response.json()
                        output_value = data['pulse']['outputValue']
                        print(f"NIST Beacon value: {output_value[:16]}...")
                        beacon_int = int(output_value, 16)
                        print(f"NIST Beacon integer: {beacon_int}")
                        return beacon_int
                    else:
                        print(f"NIST Beacon API error {response.status}, using fallback")
                        return int(time.time())

        except Exception as e:
            print(f"Error getting NIST beacon value: {e}, using fallback")
            return int(time.time())

    # ... [rest of AIProcessor methods would go here - truncated for brevity]
    # The full implementation would include all methods from ai_handler.py

class AIPlugin(BotPlugin):
    def __init__(self, openrouter_key: str = None):
        super().__init__("ai")
        self.logger = logging.getLogger(f"plugin.{self.name}")
        
        self.handler = AIProcessor()
        self.logger.info("AI plugin initialized successfully with embedded AIProcessor")
    
    def get_commands(self) -> List[str]:
        return ["8ball", "advice", "advise", "bible", "song", "nist"]
    
    async def handle_command(self, command: str, args: str, room_id: str, user_id: str) -> Optional[str]:
        self.logger.info(f"Handling {command} command from {user_id} in {room_id}")
        
        if not self.handler:
            self.logger.error("AI handler not available")
            return "❌ AI functionality not available"
        
        try:
            # All AI handler methods need a send_message_func, but we return the response instead
            # So we need to capture the response rather than letting it send directly
            
            if command == "8ball":
                # For magic 8-ball, we need to adapt the interface
                response_container = []
                
                async def capture_response(room_id, message):
                    response_container.append(message)
                
                await self.handler.handle_magic_8ball(room_id, args, False, capture_response)
                # Return all messages joined together
                return "\n".join(response_container) if response_container else "❌ No response from 8-ball"
                
            elif command in ["advice", "advise"]:
                if not args:
                    return f"❌ Please provide a question for advice. Usage: {command} <your question>"
                
                response_container = []
                async def capture_response(room_id, message):
                    response_container.append(message)
                
                is_serious = (command == "advise")
                await self.handler.handle_advice_request(room_id, args, False, is_serious, capture_response)
                # Return all messages joined together
                return "\n".join(response_container) if response_container else "❌ No advice available"
                
            elif command == "bible":
                response_container = []
                async def capture_response(room_id, message):
                    response_container.append(message)
                
                # Handle compound bible commands
                if args == "song":
                    # Import create_youtube_url function if needed
                    try:
                        from youtube_handler import create_Youtube_url
                        await self.handler.handle_bible_song(room_id, False, capture_response, create_Youtube_url)
                    except ImportError:
                        await self.handler.handle_bible_song(room_id, False, capture_response, None)
                else:
                    await self.handler.handle_bible_verse(room_id, False, capture_response)
                
                # Return all messages joined together
                return "\n".join(response_container) if response_container else "❌ No Bible verse available"
                
        except Exception as e:
            self.logger.error(f"Error handling {command} command from {user_id}: {str(e)}", exc_info=True)
            return f"❌ Error processing {command} command"
        
        return None
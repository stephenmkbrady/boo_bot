from typing import List, Optional
from plugin_base import BotPlugin

try:
    from ai_handler import AIProcessor
    AI_HANDLER_AVAILABLE = True
except ImportError:
    AI_HANDLER_AVAILABLE = False


class AIPlugin(BotPlugin):
    def __init__(self, openrouter_key: str = None):
        super().__init__("ai")
        if AI_HANDLER_AVAILABLE:
            self.handler = AIProcessor()
        else:
            self.handler = None
            self.enabled = False
    
    def get_commands(self) -> List[str]:
        return ["8ball", "advice", "bible", "song", "nist"]
    
    async def handle_command(self, command: str, args: str, room_id: str, user_id: str) -> Optional[str]:
        if not self.handler:
            return "❌ AI functionality not available"
        
        try:
            if command == "8ball":
                return await self.handler.handle_magic_8_ball(room_id, args)
            elif command == "advice":
                return await self.handler.handle_advice(room_id, args)
            elif command == "bible":
                return await self.handler.handle_bible_verse(room_id, args)
            elif command == "song":
                return await self.handler.handle_song_matching(room_id, args)
            elif command == "nist":
                return await self.handler.handle_nist_beacon(room_id, args)
        except Exception as e:
            return f"❌ Error processing {command} command: {str(e)}"
        
        return None
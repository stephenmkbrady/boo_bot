from typing import List, Optional
from plugin_base import BotPlugin

try:
    from youtube_handler import YouTubeProcessor
    YOUTUBE_HANDLER_AVAILABLE = True
except ImportError:
    YOUTUBE_HANDLER_AVAILABLE = False


class YouTubePlugin(BotPlugin):
    def __init__(self, openrouter_key: str = None):
        super().__init__("youtube")
        if YOUTUBE_HANDLER_AVAILABLE:
            self.handler = YouTubeProcessor()
        else:
            self.handler = None
            self.enabled = False
    
    def get_commands(self) -> List[str]:
        return ["summary", "subs", "ask", "videos"]
    
    async def handle_command(self, command: str, args: str, room_id: str, user_id: str) -> Optional[str]:
        if not self.handler:
            return "❌ YouTube functionality not available"
        
        try:
            if command == "summary":
                return await self.handler.handle_youtube_summary(room_id, args)
            elif command == "subs":
                return await self.handler.handle_youtube_subs(room_id, args) 
            elif command == "ask":
                return await self.handler.handle_youtube_question(room_id, args)
            elif command == "videos":
                return await self.handler.handle_youtube_videos(room_id, args)
        except Exception as e:
            return f"❌ Error processing {command} command: {str(e)}"
        
        return None
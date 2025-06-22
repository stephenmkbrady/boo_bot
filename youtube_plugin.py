from typing import List, Optional
from plugin_base import BotPlugin

try:
    from youtube_handler import YouTubeProcessor
    YOUTUBE_HANDLER_AVAILABLE = True
except ImportError:
    YOUTUBE_HANDLER_AVAILABLE = False


class YouTubePlugin(BotPlugin):
    def __init__(self, openrouter_key: str = None, bot_instance=None):
        super().__init__("youtube")
        self.bot = bot_instance
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
            # All YouTube handler methods need send_message_func, but we return the response instead
            # So we need to capture the response rather than letting it send directly
            
            if command == "summary":
                if not args:
                    return "❌ Please provide a YouTube URL. Usage: summary <youtube_url>"
                
                # Send immediate feedback
                if self.bot:
                    await self.bot.send_message(room_id, "🎬 Processing YouTube summary... This may take a moment.")
                
                response_container = []
                async def capture_response(room_id, message):
                    response_container.append(message)
                
                await self.handler.handle_youtube_summary(room_id, args, False, capture_response)
                # Return all messages joined together
                return "\n".join(response_container) if response_container else "❌ No summary available"
                
            elif command == "subs":
                if not args:
                    return "❌ Please provide a YouTube URL. Usage: subs <youtube_url>"
                
                # Send immediate feedback
                if self.bot:
                    await self.bot.send_message(room_id, "📝 Downloading and processing subtitles... This may take a moment.")
                
                response_container = []
                async def capture_response(room_id, message):
                    response_container.append(message)
                
                # Note: subs may also send file attachments, but for now we'll just capture text responses
                await self.handler.handle_youtube_subs(room_id, args, False, capture_response, None)
                # Return all messages joined together
                return "\n".join(response_container) if response_container else "❌ No subtitles available"
                
            elif command == "ask":
                if not args:
                    return "❌ Please provide a question. Usage: ask <question> or ask <youtube_url> <question>"
                
                response_container = []
                async def capture_response(room_id, message):
                    response_container.append(message)
                
                await self.handler.handle_youtube_question(room_id, args, False, capture_response, "bot")
                # Return all messages joined together
                return "\n".join(response_container) if response_container else "❌ No answer available"
                
            elif command == "videos":
                response_container = []
                async def capture_response(room_id, message):
                    response_container.append(message)
                
                await self.handler.handle_list_videos(room_id, False, capture_response, "bot")
                # Return all messages joined together
                return "\n".join(response_container) if response_container else "❌ No videos found"
                
        except Exception as e:
            return f"❌ Error processing {command} command: {str(e)}"
        
        return None
from typing import List, Optional
import logging
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
        self.logger = logging.getLogger(f"plugin.{self.name}")
        
        if YOUTUBE_HANDLER_AVAILABLE:
            self.handler = YouTubeProcessor()
            self.logger.info("YouTube plugin initialized successfully")
        else:
            self.handler = None
            self.enabled = False
            self.logger.warning("YouTube plugin disabled - YouTubeProcessor not available")
    
    def get_commands(self) -> List[str]:
        return ["summary", "subs", "ask", "videos"]
    
    async def handle_command(self, command: str, args: str, room_id: str, user_id: str) -> Optional[str]:
        self.logger.info(f"Handling {command} command from {user_id} in {room_id}")
        
        if not self.handler:
            self.logger.error("YouTube handler not available")
            return "❌ YouTube functionality not available"
        
        try:
            # All YouTube handler methods need send_message_func, but we return the response instead
            # So we need to capture the response rather than letting it send directly
            
            if command == "summary":
                if not args:
                    self.logger.warning(f"Summary command called without URL by {user_id}")
                    return "❌ Please provide a YouTube URL. Usage: summary <youtube_url>"
                
                self.logger.info(f"Processing YouTube summary for URL: {args[:100]}...")
                
                # Send immediate feedback
                if self.bot:
                    await self.bot.send_message(room_id, "🎬 Processing YouTube summary... This may take a moment.")
                
                response_container = []
                async def capture_response(room_id, message):
                    response_container.append(message)
                
                await self.handler.handle_youtube_summary(room_id, args, False, capture_response)
                result = "\n".join(response_container) if response_container else "❌ No summary available"
                
                if response_container:
                    self.logger.info(f"YouTube summary completed successfully for {user_id}")
                else:
                    self.logger.warning(f"No summary generated for {user_id} with URL: {args[:100]}")
                
                return result
                
            elif command == "subs":
                if not args:
                    self.logger.warning(f"Subs command called without URL by {user_id}")
                    return "❌ Please provide a YouTube URL. Usage: subs <youtube_url>"
                
                self.logger.info(f"Processing YouTube subtitles for URL: {args[:100]}...")
                
                # Send immediate feedback
                if self.bot:
                    await self.bot.send_message(room_id, "📝 Downloading and processing subtitles... This may take a moment.")
                
                response_container = []
                async def capture_response(room_id, message):
                    response_container.append(message)
                
                # Note: subs may also send file attachments, but for now we'll just capture text responses
                await self.handler.handle_youtube_subs(room_id, args, False, capture_response, None)
                result = "\n".join(response_container) if response_container else "❌ No subtitles available"
                
                if response_container:
                    self.logger.info(f"YouTube subtitles processed successfully for {user_id}")
                else:
                    self.logger.warning(f"No subtitles generated for {user_id} with URL: {args[:100]}")
                
                return result
                
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
            self.logger.error(f"Error handling {command} command from {user_id}: {str(e)}", exc_info=True)
            return f"❌ Error processing {command} command"
        
        return None
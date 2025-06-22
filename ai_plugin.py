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
        return ["8ball", "advice", "advise", "bible", "song", "nist"]
    
    async def handle_command(self, command: str, args: str, room_id: str, user_id: str) -> Optional[str]:
        if not self.handler:
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
            return f"❌ Error processing {command} command: {str(e)}"
        
        return None
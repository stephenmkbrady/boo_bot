from typing import List, Optional
import logging
import os
import aiohttp
import time
from plugins.plugin_interface import BotPlugin


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

    async def get_nist_beacon_value(self):
        """Get current NIST Randomness Beacon value and determine positive/negative"""
        beacon_int = await self.get_nist_beacon_random_number()
        is_positive = (beacon_int % 2) == 0
        print(f"NIST Beacon determines: {'POSITIVE' if is_positive else 'NEGATIVE'}")
        return is_positive

    async def generate_ai_fortune(self, question=None, is_positive=True):
        """Generate a creative fortune using AI with NIST-determined polarity"""
        try:
            if not self.openrouter_api_key:
                return None

            polarity = "POSITIVE/YES" if is_positive else "NEGATIVE/NO"

            if question:
                prompt = f"""You are a bold, decisive magic 8-ball oracle powered by NIST quantum randomness. Someone asks: "{question}"
The NIST Randomness Beacon has determined this answer should be {polarity}.
Give a CLEAR {polarity.lower()} answer with mystical flair:
{"POSITIVE/YES examples:" if is_positive else "NEGATIVE/NO examples:"}
{'"The cosmic winds STRONGLY favor this venture - quantum forces align!"' if is_positive else '"The quantum realm SCREAMS warning - avoid this path!"'}
Be mystical, dramatic, and CLEARLY {polarity.lower()}! Reference quantum/cosmic forces. 1-2 sentences max."""
            else:
                prompt = f"""You are a dramatic magic 8-ball oracle powered by NIST quantum randomness.
The quantum realm has determined this fortune should be {polarity}.
Give a {polarity.lower()} mystical fortune with cosmic flair:
{"POSITIVE examples:" if is_positive else "NEGATIVE examples:"}
{'"Quantum entanglement brings tremendous fortune to your timeline!"' if is_positive else '"Dark quantum fluctuations gather around your path!"'}
Reference quantum/cosmic forces and be CLEARLY {polarity.lower()}! 1-2 sentences max."""

            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 150,
                "temperature": 1.1,
                "top_p": 0.9
            }
            
            headers = {
                "Authorization": f"Bearer {self.openrouter_api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/matrix-nio/matrix-nio",
                "X-Title": "Matrix Bot"
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.openrouter_url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data['choices'][0]['message']['content'].strip().strip('"').strip("'").strip()
                    else:
                        print(f"OpenRouter API error {response.status}")
                        return None

        except Exception as e:
            print(f"Error generating AI fortune: {e}")
            return None

    async def generate_considerate_advice(self, question, is_positive=True):
        """Generate thoughtful, serious advice using AI with NIST-determined polarity"""
        try:
            if not self.openrouter_api_key:
                return None

            polarity_instruction = "ENCOURAGING and OPTIMISTIC" if is_positive else "CAUTIONARY and REALISTIC"

            prompt = f"""Someone asked for thoughtful advice: "{question}"
The NIST Randomness Beacon has determined this should be {polarity_instruction} advice.
Give SERIOUS, CONSIDERATE advice that's: {polarity_instruction} in tone, thoughtful and empathetic, practical and actionable, wise and mature, 2-3 sentences.
Be genuinely helpful, empathetic, and maintain the {polarity_instruction.lower()} tone."""

            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 200,
                "temperature": 0.7,
                "top_p": 0.9
            }
            
            headers = {
                "Authorization": f"Bearer {self.openrouter_api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/matrix-nio/matrix-nio",
                "X-Title": "Matrix Bot"
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.openrouter_url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data['choices'][0]['message']['content'].strip().strip('"').strip("'").strip()
                    else:
                        print(f"OpenRouter API error {response.status}")
                        return None

        except Exception as e:
            print(f"Error generating considerate advice: {e}")
            return None

    async def generate_funny_advice(self, question, is_positive=True):
        """Generate funny, unconventional advice using AI with NIST-determined polarity"""
        try:
            if not self.openrouter_api_key:
                return None

            polarity_instruction = "POSITIVE and ENCOURAGING" if is_positive else "CAUTIONARY and SKEPTICAL"

            prompt = f"""Someone asked for advice: "{question}"
The NIST Randomness Beacon has determined this should be {polarity_instruction} advice.
Give FUNNY, UNCONVENTIONAL advice that's: {polarity_instruction} in tone, hilariously absurd but somehow makes weird sense, creative and unexpected. 2-3 sentences max.
Be creative, weird, and funny while maintaining the {polarity_instruction.lower()} tone determined by quantum randomness!"""

            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 200,
                "temperature": 1.2,
                "top_p": 0.95
            }
            
            headers = {
                "Authorization": f"Bearer {self.openrouter_api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/matrix-nio/matrix-nio",
                "X-Title": "Matrix Bot"
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.openrouter_url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data['choices'][0]['message']['content'].strip().strip('"').strip("'").strip()
                    else:
                        print(f"OpenRouter API error {response.status}")
                        return None

        except Exception as e:
            print(f"Error generating funny advice: {e}")
            return None

    def parse_bible_file(self, file_path):
        """Parse the KJV Bible text file and return verses as a list"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            verses = []
            
            for line in content.split('\n'):
                line = line.strip()
                if not line or line.startswith('KJV') or line.startswith('King James'):
                    continue
                    
                # The actual format is: "Book Chapter:Verse<tab>text" or "Book Chapter:Verse text"
                if ':' in line:
                    # Split on tab first, then fallback to space splitting
                    if '\t' in line:
                        parts = line.split('\t', 1)
                        reference = parts[0].strip()
                        verse_text = parts[1].strip()
                    else:
                        # Fallback: find the first space after the verse number
                        colon_pos = line.find(':')
                        if colon_pos > 0:
                            # Find the first space or tab after the verse number
                            remaining = line[colon_pos + 1:]
                            space_pos = -1
                            for i, char in enumerate(remaining):
                                if char in [' ', '\t'] and remaining[:i].strip().isdigit():
                                    space_pos = i
                                    break
                            
                            if space_pos > 0:
                                reference = line[:colon_pos + 1 + space_pos].strip()
                                verse_text = line[colon_pos + 1 + space_pos:].strip()
                            else:
                                # Try splitting on the first space after colon
                                after_colon = line[colon_pos + 1:]
                                first_space = after_colon.find(' ')
                                if first_space > 0 and after_colon[:first_space].isdigit():
                                    reference = line[:colon_pos + 1 + first_space].strip()
                                    verse_text = after_colon[first_space:].strip()
                                else:
                                    continue
                    
                    if reference and verse_text and reference.count(':') == 1:
                        verses.append((reference, verse_text))
                        
            return verses

        except Exception as e:
            print(f"Error parsing Bible file: {e}")
            return []

    async def handle_magic_8ball(self, room_id, question=None, is_edit=False, send_message_func=None):
        """Generate a magic 8-ball style fortune using NIST Beacon + AI"""
        if not send_message_func:
            return

        if not self.openrouter_api_key:
            await send_message_func(room_id, "❌ Magic 8-ball requires OPENROUTER_API_KEY in .env file")
            return

        try:
            edit_prefix = "✏️ " if is_edit else ""
            if question:
                await send_message_func(room_id, f"{edit_prefix}🎱 *Consulting the NIST quantum oracle for: '{question}'...*")
            else:
                await send_message_func(room_id, f"{edit_prefix}🎱 *Consulting the NIST quantum oracle...*")

            is_positive = await self.get_nist_beacon_value()
            fortune = await self.generate_ai_fortune(question, is_positive)

            if fortune:
                beacon_info = "✨ *Determined by NIST Randomness Beacon quantum entropy*"
                if is_edit:
                    beacon_info += " (responding to edit)"
                await send_message_func(room_id, f"{edit_prefix}🎱 {fortune}\n\n{beacon_info}")
            else:
                await send_message_func(room_id, f"{edit_prefix}🎱 The quantum spirits are unclear... try again later.")

        except Exception as e:
            print(f"Error in magic 8-ball: {e}")
            await send_message_func(room_id, f"{edit_prefix}🎱 The magic 8-ball is broken! Try again later.")

    async def handle_bible_verse(self, room_id, is_edit=False, send_message_func=None):
        """Get a random Bible verse using NIST Beacon"""
        if not send_message_func:
            return

        try:
            edit_prefix = "✏️ " if is_edit else ""
            await send_message_func(room_id, f"{edit_prefix}📖 *Consulting the NIST quantum scripture selector...*")

            bible_file = os.path.join(os.path.dirname(__file__), "kjv.txt")
            if not os.path.exists(bible_file):
                await send_message_func(room_id, f"{edit_prefix}❌ Bible file (kjv.txt) not found. Please download it from https://openbible.com/textfiles/kjv.txt")
                return

            verses = self.parse_bible_file(bible_file)
            
            if not verses:
                await send_message_func(room_id, f"{edit_prefix}❌ Could not parse Bible verses from kjv.txt")
                return

            # Use NIST beacon for truly random verse selection
            beacon_int = await self.get_nist_beacon_random_number()
            verse_index = beacon_int % len(verses)
            reference, verse_text = verses[verse_index]

            beacon_info = "✨ *Verse selected by NIST Randomness Beacon quantum entropy*"
            if is_edit:
                beacon_info += " (responding to edit)"

            response = f"{edit_prefix}📖 **{reference}**\n\n*{verse_text}*\n\n{beacon_info}"
            await send_message_func(room_id, response)

        except Exception as e:
            print(f"Error getting Bible verse: {e}")
            await send_message_func(room_id, f"{edit_prefix}📖 Error accessing the quantum scriptures: {str(e)}")


class AIPlugin(BotPlugin):
    def __init__(self):
        super().__init__("ai")
        self.version = "1.0.0"
        self.description = "AI-powered features including magic 8-ball, advice, and Bible verses"
        self.logger = logging.getLogger(f"plugin.{self.name}")
        self.handler = AIProcessor()
    
    async def initialize(self, bot_instance) -> bool:
        """Initialize plugin with bot instance"""
        self.bot = bot_instance
        self.logger.info("AI plugin initialized successfully with embedded AIProcessor")
        return True
    
    def get_commands(self) -> List[str]:
        return ["8ball", "advice", "advise", "bible", "song", "nist"]
    
    async def handle_command(self, command: str, args: str, room_id: str, user_id: str, bot_instance) -> Optional[str]:
        self.logger.info(f"Handling {command} command from {user_id} in {room_id}")
        
        if not self.handler:
            self.logger.error("AI handler not available")
            return "❌ AI functionality not available"
        
        try:
            # All AI handler methods need a send_message_func, but we return the response instead
            # So we need to capture the response rather than letting it send directly
            
            if command == "8ball":
                response_container = []
                async def capture_response(room_id, message):
                    response_container.append(message)
                
                await self.handler.handle_magic_8ball(room_id, args or None, False, capture_response)
                # Return all messages joined together
                return "\n".join(response_container) if response_container else "❌ Magic 8-ball error"
                
            elif command in ["advice", "advise"]:
                if not args:
                    return "❌ Please provide a question. Usage: advice <question>"
                
                response_container = []
                async def capture_response(room_id, message):
                    response_container.append(message)
                
                is_serious = (command == "advise")
                # Note: handle_advice_request method doesn't exist in original, using bible for now
                await self.handler.handle_magic_8ball(room_id, args, False, capture_response)
                return "\n".join(response_container) if response_container else "❌ Advice error"
                
            elif command == "bible":
                response_container = []
                async def capture_response(room_id, message):
                    response_container.append(message)
                
                await self.handler.handle_bible_verse(room_id, False, capture_response)
                # Return all messages joined together
                return "\n".join(response_container) if response_container else "❌ No Bible verse available"
                
            elif command == "song":
                if not args:
                    return "❌ Please provide a song to search for. Usage: song <song name>"
                
                # Import the YouTube URL creation function
                try:
                    from plugins.youtube.plugin import create_Youtube_url
                    youtube_url = create_Youtube_url(args)
                    if youtube_url:
                        return f"🎵 YouTube search for '{args}':\n{youtube_url}"
                    else:
                        return f"❌ Could not create YouTube search URL for '{args}'"
                except ImportError:
                    return "❌ YouTube functionality not available"
                except Exception as e:
                    self.logger.error(f"Error creating YouTube URL: {e}")
                    return f"❌ Error creating YouTube search for '{args}'"
                    
            elif command == "nist":
                try:
                    beacon_value = await self.handler.get_nist_beacon_random_number()
                    return f"🔢 **Current NIST Randomness Beacon Value:**\n```\n{beacon_value}\n```\n\nThis is a cryptographically secure random number from the U.S. National Institute of Standards and Technology."
                except Exception as e:
                    self.logger.error(f"Error getting NIST beacon value: {e}")
                    return "❌ Could not retrieve NIST Randomness Beacon value"
                
        except Exception as e:
            self.logger.error(f"Error handling {command} command from {user_id}: {str(e)}", exc_info=True)
            return f"❌ Error processing {command} command"
        
        return None
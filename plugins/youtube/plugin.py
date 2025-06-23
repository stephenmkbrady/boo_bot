import yt_dlp
import os
import tempfile
import logging
import urllib.parse
import subprocess
import re
import aiohttp
import asyncio
from datetime import datetime
from collections import OrderedDict
from typing import Optional, Tuple, List
from plugins.plugin_interface import BotPlugin

def youtube_handler(url):
    """
    Download audio from YouTube URL and return the file path.
    
    Args:
        url (str): YouTube URL to download
        
    Returns:
        str: Path to the downloaded audio file, or None if failed
    """
    try:
        # Create a temporary directory for downloads
        temp_dir = tempfile.mkdtemp()
        
        # Configure yt-dlp options
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
            'extractaudio': True,
            'audioformat': 'mp3',
            'noplaylist': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extract info about the video
            info = ydl.extract_info(url, download=False)
            
            # Get the title for naming
            title = info.get('title', 'Unknown')
            print(f"🎵 Found video: {title}")
            
            # Download the audio
            ydl.download([url])
            
            # Find the downloaded file
            for file in os.listdir(temp_dir):
                if file.endswith(('.mp3', '.m4a', '.webm', '.ogg')):
                    full_path = os.path.join(temp_dir, file)
                    print(f"✅ Downloaded: {full_path}")
                    return full_path
                    
        print("❌ No audio file found after download")
        return None
        
    except Exception as e:
        print(f"❌ Error downloading YouTube audio: {e}")
        return None

def create_Youtube_url(song_text):
    """
    Create a YouTube search URL for a song.
    
    Args:
        song_text (str): Song text, can be in format '"Song" by Artist' or just 'Song'
        
    Returns:
        str: YouTube search URL
    """
    try:
        # Check if the input follows the '"Song" by Artist' pattern
        match = re.match(r'^"([^"]+)"\s+by\s+(.+)', song_text)
        if match:
            song_name = match.group(1)
            artist_name = match.group(2)
            # Format as "Artist Song" for better YouTube search results
            query = f"{artist_name} {song_name}"
        else:
            query = song_text
        
        # URL encode the query
        encoded_query = urllib.parse.quote_plus(query)
        
        # Create YouTube search URL
        youtube_url = f"https://www.youtube.com/results?search_query={encoded_query}"
        
        print(f"🔍 Created YouTube search URL: {youtube_url}")
        return youtube_url
        
    except Exception as e:
        print(f"❌ Error creating YouTube URL: {e}")
        return None

class YouTubeProcessor:
    """Class to handle YouTube video processing, summarization, and Q&A functionality"""
    
    def __init__(self, chunk_size=8000, chunk_overlap=800, max_chunks=10, max_cached_transcripts_per_room=5):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.max_chunks = max_chunks
        self.max_cached_transcripts_per_room = max_cached_transcripts_per_room
        self.transcript_cache = {}  # room_id -> OrderedDict of URL -> (title, transcript, timestamp)
        self.last_processed_video = {}  # room_id -> most recent video URL

    async def handle_youtube_summary(self, room_id, url, is_edit=False, send_message_func=None):
        """Handle YouTube video summarization"""
        try:
            # Check for required dependencies
            if not os.getenv("OPENROUTER_API_KEY"):
                if send_message_func:
                    await send_message_func(room_id, "❌ YouTube summary feature requires OPENROUTER_API_KEY in .env file")
                return

            edit_prefix = "✏️ " if is_edit else ""
            if send_message_func:
                await send_message_func(room_id, f"{edit_prefix}🔄 Extracting subtitles from YouTube video...")

            # Extract subtitles using yt-dlp
            subtitles = await self.extract_youtube_subtitles(url)

            if not subtitles:
                if send_message_func:
                    await send_message_func(room_id, f"{edit_prefix}❌ No subtitles found for this video. The video might not have subtitles or be unavailable.")
                return

            if send_message_func:
                await send_message_func(room_id, f"{edit_prefix}🤖 Generating summary using AI...")

            # Get video title
            title = await self.get_youtube_title(url)

            # Cache the transcript for Q&A functionality (per room)
            self.cache_transcript(url, title, subtitles, room_id)

            # Summarize using OpenRouter AI
            summary = await self.summarize_with_ai(subtitles, title)

            if summary:
                # Format the response
                response = f"""{edit_prefix}📺 **{title}**

**Summary:**
{summary}

💡 Ask questions about this video using: **youtube: <your question>**"""

                if send_message_func:
                    await send_message_func(room_id, response)
            else:
                if send_message_func:
                    await send_message_func(room_id, f"{edit_prefix}❌ Failed to generate summary. Please try again later.")

        except Exception as e:
            print(f"❌ Error processing YouTube summary: {e}")
            if send_message_func:
                await send_message_func(room_id, f"{edit_prefix}❌ Error processing video: {str(e)}")

    async def handle_youtube_subs(self, room_id, url, is_edit=False, send_message_func=None, bot_instance=None):
        """Handle YouTube subtitles extraction and upload as file"""
        try:
            edit_prefix = "✏️ " if is_edit else ""
            if send_message_func:
                await send_message_func(room_id, f"{edit_prefix}🔄 Extracting subtitles from YouTube video...")

            # Extract subtitles using yt-dlp
            subtitles = await self.extract_youtube_subtitles(url)

            if not subtitles:
                if send_message_func:
                    await send_message_func(room_id, f"{edit_prefix}❌ No subtitles found for this video.")
                return

            # Get video title
            title = await self.get_youtube_title(url)

            # Cache the transcript for Q&A functionality (per room)
            self.cache_transcript(url, title, subtitles, room_id)

            # Create a safe filename from the video title
            safe_title = re.sub(r'[^\w\s-]', '', title).strip()
            safe_title = re.sub(r'[-\s]+', '-', safe_title)[:50]  # Limit length
            filename = f"{safe_title}_subtitles.txt"

            # Create temporary file with subtitles
            temp_file_path = os.path.join(tempfile.gettempdir(), filename)
            
            try:
                with open(temp_file_path, 'w', encoding='utf-8') as f:
                    f.write(f"YouTube Video Subtitles\n")
                    f.write(f"Title: {title}\n")
                    f.write(f"URL: {url}\n")
                    f.write(f"Extracted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"{'-' * 50}\n\n")
                    f.write(subtitles)

                # Upload the file using bot's send_file method
                if bot_instance and hasattr(bot_instance, 'send_file'):
                    success = await bot_instance.send_file(room_id, temp_file_path, filename, "text/plain")
                    
                    if success:
                        # Send confirmation message
                        response = f"""{edit_prefix}📺 **{title}**

✅ Subtitles uploaded as file: **{filename}**

💡 Ask questions about this video using: **youtube: <your question>**"""
                        
                        if send_message_func:
                            await send_message_func(room_id, response)
                    else:
                        # Fallback to text if file upload fails
                        await self._send_subtitles_as_text(room_id, title, subtitles, edit_prefix, send_message_func)
                else:
                    # Fallback to text if no bot instance
                    await self._send_subtitles_as_text(room_id, title, subtitles, edit_prefix, send_message_func)
                    
            finally:
                # Clean up temporary file
                try:
                    if os.path.exists(temp_file_path):
                        os.remove(temp_file_path)
                except Exception as cleanup_error:
                    print(f"⚠️ Warning: Could not clean up temp file {temp_file_path}: {cleanup_error}")

        except Exception as e:
            print(f"❌ Error extracting YouTube subtitles: {e}")
            if send_message_func:
                await send_message_func(room_id, f"{edit_prefix}❌ Error extracting subtitles: {str(e)}")
    
    async def _send_subtitles_as_text(self, room_id, title, subtitles, edit_prefix, send_message_func):
        """Fallback method to send subtitles as text (original behavior)"""
        response = f"""{edit_prefix}📺 **{title}**

**Subtitles:**
{subtitles[:4000]}{'...(truncated)' if len(subtitles) > 4000 else ''}

💡 Ask questions about this video using: **youtube: <your question>**"""

        if send_message_func:
            await send_message_func(room_id, response)

    async def extract_youtube_subtitles(self, url):
        """Extract subtitles from YouTube video using yt-dlp"""
        try:
            ydl_opts = {
                'writesubtitles': True,
                'writeautomaticsub': True,
                'subtitleslangs': ['en'],
                'skip_download': True,
                'quiet': True
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                # Try to get manual subtitles first, then automatic
                subtitles_data = info.get('subtitles', {})
                automatic_captions = info.get('automatic_captions', {})
                
                subtitle_url = None
                
                # Prefer manual subtitles
                if 'en' in subtitles_data and subtitles_data['en']:
                    subtitle_url = subtitles_data['en'][0]['url']
                elif 'en' in automatic_captions and automatic_captions['en']:
                    # Find VTT format in automatic captions
                    for caption in automatic_captions['en']:
                        if caption.get('ext') == 'vtt':
                            subtitle_url = caption['url']
                            break
                
                if subtitle_url:
                    # Download and parse the subtitle content
                    async with aiohttp.ClientSession() as session:
                        async with session.get(subtitle_url) as response:
                            if response.status == 200:
                                vtt_content = await response.text()
                                return self.parse_vtt(vtt_content)
                
            return None
                
        except Exception as e:
            print(f"❌ Error extracting subtitles: {e}")
            return None

    def parse_vtt(self, vtt_content):
        """Parse VTT subtitle content and extract clean text"""
        try:
            lines = vtt_content.split('\n')
            text_lines = []
            
            for line in lines:
                line = line.strip()
                # Skip empty lines, timestamp lines, and VTT headers
                if (line and 
                    not line.startswith('WEBVTT') and 
                    not line.startswith('NOTE') and
                    not '-->' in line and
                    not re.match(r'^\d+$', line)):
                    
                    # Remove HTML tags and clean up - do this for ALL lines with content
                    clean_line = re.sub(r'<[^>]+>', '', line)
                    clean_line = re.sub(r'&[a-zA-Z]+;', '', clean_line)  # Remove HTML entities
                    clean_line = clean_line.strip()
                    
                    if clean_line:
                        text_lines.append(clean_line)
            
            return ' '.join(text_lines)
            
        except Exception as e:
            print(f"❌ Error parsing VTT: {e}")
            return None

    async def get_youtube_title(self, url):
        """Get the title of a YouTube video"""
        try:
            ydl_opts = {
                'quiet': True,
                'skip_download': True
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return info.get('title', 'Unknown Video')
                
        except Exception as e:
            print(f"❌ Error getting video title: {e}")
            return "Unknown Video"

    def cache_transcript(self, url, title, transcript, room_id):
        """Cache transcript for Q&A functionality (per room)"""
        try:
            if room_id not in self.transcript_cache:
                self.transcript_cache[room_id] = OrderedDict()
            
            room_cache = self.transcript_cache[room_id]
            
            # Add/update the transcript
            room_cache[url] = (title, transcript, datetime.now())
            
            # Remove oldest entries if we exceed the limit
            while len(room_cache) > self.max_cached_transcripts_per_room:
                room_cache.popitem(last=False)  # Remove oldest
            
            # Update last processed video for this room
            self.last_processed_video[room_id] = url
            
            print(f"📚 Cached transcript for room {room_id}: {title}")
            
        except Exception as e:
            print(f"❌ Error caching transcript: {e}")

    async def summarize_with_ai(self, transcript, title):
        """Summarize transcript using OpenRouter AI"""
        try:
            api_key = os.getenv("OPENROUTER_API_KEY")
            if not api_key:
                return None
            
            # Chunk the transcript if it's too long
            chunks = self.chunk_text(transcript)
            
            summaries = []
            for i, chunk in enumerate(chunks[:self.max_chunks]):
                chunk_summary = await self.summarize_chunk(chunk, title, api_key, i + 1, len(chunks))
                if chunk_summary:
                    summaries.append(chunk_summary)
            
            if summaries:
                if len(summaries) == 1:
                    return summaries[0]
                else:
                    # Combine multiple chunk summaries
                    combined_summary = await self.combine_summaries(summaries, title, api_key)
                    return combined_summary if combined_summary else '\n'.join(summaries)
            
            return None
            
        except Exception as e:
            print(f"❌ Error in AI summarization: {e}")
            return None

    def chunk_text(self, text, chunk_size=None, overlap=None):
        """Split text into overlapping chunks"""
        if chunk_size is None:
            chunk_size = self.chunk_size
        if overlap is None:
            overlap = self.chunk_overlap
            
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            chunks.append(chunk)
            start = end - overlap
            
        return chunks

    async def summarize_chunk(self, chunk, title, api_key, chunk_num, total_chunks):
        """Summarize a single chunk of text"""
        try:
            prompt = f"""Please provide a concise summary of this part of the video transcript for "{title}".

Transcript excerpt (part {chunk_num} of {total_chunks}):
{chunk}

Provide a clear, informative summary of the main points discussed in this section:"""

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "cognitivecomputations/dolphin3.0-mistral-24b:free",
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 500,
                        "temperature": 0.3
                    }
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data['choices'][0]['message']['content'].strip()
                    else:
                        print(f"❌ OpenRouter API error: {response.status}")
                        return None
                        
        except Exception as e:
            print(f"❌ Error summarizing chunk: {e}")
            return None

    async def combine_summaries(self, summaries, title, api_key):
        """Combine multiple chunk summaries into a final summary"""
        try:
            combined_text = '\n\n'.join([f"Section {i+1}: {summary}" for i, summary in enumerate(summaries)])
            
            prompt = f"""Please create a comprehensive summary by combining these section summaries for the video "{title}".

Section summaries:
{combined_text}

Provide a well-structured, comprehensive summary that captures the main themes and key points:"""

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "cognitivecomputations/dolphin3.0-mistral-24b:free",
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 800,
                        "temperature": 0.3
                    }
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data['choices'][0]['message']['content'].strip()
                    else:
                        print(f"❌ OpenRouter API error: {response.status}")
                        return None
                        
        except Exception as e:
            print(f"❌ Error combining summaries: {e}")
            return None

    async def handle_youtube_question(self, room_id, question, is_edit=False, send_message_func=None):
        """Answer questions about cached YouTube transcripts"""
        try:
            edit_prefix = "✏️ " if is_edit else ""
            
            # Check if we have cached transcripts for this room
            if room_id not in self.transcript_cache or not self.transcript_cache[room_id]:
                if send_message_func:
                    await send_message_func(room_id, f"{edit_prefix}❌ No YouTube videos have been processed in this room yet. Use **youtube summary <URL>** first.")
                return
            
            # Get the most recent video transcript
            room_cache = self.transcript_cache[room_id]
            latest_url = list(room_cache.keys())[-1]  # Most recently added
            title, transcript, timestamp = room_cache[latest_url]
            
            if send_message_func:
                await send_message_func(room_id, f"{edit_prefix}🤖 Analyzing transcript and generating answer...")
            
            # Generate answer using AI
            answer = await self.answer_question_with_ai(question, transcript, title)
            
            if answer:
                response = f"""{edit_prefix}🎯 **Question about "{title}"**

**Q:** {question}

**A:** {answer}"""
                
                if send_message_func:
                    await send_message_func(room_id, response)
            else:
                if send_message_func:
                    await send_message_func(room_id, f"{edit_prefix}❌ Failed to generate answer. Please try again later.")
                    
        except Exception as e:
            print(f"❌ Error handling YouTube question: {e}")
            if send_message_func:
                await send_message_func(room_id, f"{edit_prefix}❌ Error processing question: {str(e)}")

    async def answer_question_with_ai(self, question, transcript, title):
        """Answer a question using the video transcript"""
        try:
            api_key = os.getenv("OPENROUTER_API_KEY")
            if not api_key:
                return None
            
            # Truncate transcript if too long
            max_context_length = 12000
            if len(transcript) > max_context_length:
                transcript = transcript[:max_context_length] + "...(transcript truncated)"
            
            prompt = f"""Based on the following video transcript for "{title}", please answer the user's question accurately and helpfully.

Video Transcript:
{transcript}

User Question: {question}

Please provide a clear, accurate answer based only on the information available in the transcript. If the question cannot be answered from the transcript, please say so:"""

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "cognitivecomputations/dolphin3.0-mistral-24b:free",
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 600,
                        "temperature": 0.2
                    }
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data['choices'][0]['message']['content'].strip()
                    else:
                        print(f"❌ OpenRouter API error: {response.status}")
                        return None
                        
        except Exception as e:
            print(f"❌ Error answering question: {e}")
            return None


class YouTubePlugin(BotPlugin):
    def __init__(self):
        super().__init__("youtube")
        self.version = "1.0.0"
        self.description = "YouTube video processing, summarization, and Q&A functionality"
        self.processor = YouTubeProcessor()
        self.logger = logging.getLogger(f"plugin.{self.name}")
        
    def get_commands(self) -> List[str]:
        return ["youtube", "yt"]
    
    async def initialize(self, bot_instance) -> bool:
        """Initialize the YouTube plugin"""
        try:
            self.bot = bot_instance
            self.logger.info("YouTube plugin initialized successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize YouTube plugin: {e}")
            return False
    
    async def handle_command(self, command: str, args: str, room_id: str, user_id: str, bot_instance) -> Optional[str]:
        """Handle YouTube commands"""
        self.logger.info(f"Handling {command} command from {user_id} in {room_id}")
        
        try:
            if command in ["youtube", "yt"]:
                return await self._handle_youtube_command(args, room_id, user_id, bot_instance)
        except Exception as e:
            self.logger.error(f"Error handling {command} command from {user_id}: {str(e)}", exc_info=True)
            return f"❌ Error processing YouTube command"
        
        return None
    
    async def _handle_youtube_command(self, args: str, room_id: str, user_id: str, bot_instance) -> str:
        """Handle youtube command with subcommands"""
        if not args:
            return """📺 **YouTube Commands:**

• **youtube summary <URL>** - Get AI summary of video
• **youtube subs <URL>** - Get video subtitles
• **youtube <question>** - Ask questions about the last processed video

**Examples:**
• `youtube summary https://youtu.be/dQw4w9WgXcQ`
• `youtube What are the main points discussed?`"""
        
        parts = args.split(" ", 1)
        subcommand = parts[0].lower()
        
        if subcommand == "summary" and len(parts) > 1:
            url = parts[1].strip()
            if self._is_youtube_url(url):
                # Process in background and return immediate feedback
                asyncio.create_task(
                    self.processor.handle_youtube_summary(room_id, url, False, bot_instance.send_message)
                )
                return f"🔄 Processing YouTube summary for: {url}"
            else:
                return "❌ Please provide a valid YouTube URL"
        
        elif subcommand == "subs" and len(parts) > 1:
            url = parts[1].strip()
            if self._is_youtube_url(url):
                # Process in background and return immediate feedback
                asyncio.create_task(
                    self.processor.handle_youtube_subs(room_id, url, False, bot_instance.send_message, bot_instance)
                )
                return f"🔄 Extracting subtitles from: {url}"
            else:
                return "❌ Please provide a valid YouTube URL"
        
        else:
            # Treat as question about cached video
            question = args
            # Process in background and return immediate feedback
            asyncio.create_task(
                self.processor.handle_youtube_question(room_id, question, False, bot_instance.send_message)
            )
            return f"🤖 Analyzing question: {question}"
    
    def _is_youtube_url(self, url: str) -> bool:
        """Check if URL is a valid YouTube URL"""
        youtube_patterns = [
            r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=[\w-]+',
            r'(?:https?://)?(?:www\.)?youtu\.be/[\w-]+',
            r'(?:https?://)?(?:www\.)?youtube\.com/embed/[\w-]+',
            r'(?:https?://)?(?:www\.)?youtube\.com/v/[\w-]+'
        ]
        
        return any(re.match(pattern, url) for pattern in youtube_patterns)
    
    async def cleanup(self):
        """Cleanup when plugin is unloaded"""
        self.logger.info("YouTube plugin cleanup completed")
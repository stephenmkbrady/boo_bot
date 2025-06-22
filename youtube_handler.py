import yt_dlp
import os
import tempfile
import logging
import urllib.parse
import subprocess
import re
import aiohttp
from datetime import datetime
from collections import OrderedDict
from typing import Optional, Tuple

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
            'audioquality': '192K',
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extract info to get the title
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'Unknown')
            
            # Download the audio
            ydl.download([url])
            
            # Find the downloaded file
            for file in os.listdir(temp_dir):
                if file.endswith(('.mp3', '.m4a', '.webm', '.ogg')):
                    file_path = os.path.join(temp_dir, file)
                    logging.info(f"Downloaded YouTube audio: {title} -> {file_path}")
                    return file_path
            
            logging.error(f"No audio file found after download for: {url}")
            return None
            
    except Exception as e:
        logging.error(f"Error downloading YouTube audio from {url}: {str(e)}")
        return None

def create_Youtube_url(song_text):
    """Create a Youtube URL from song title and artist"""
    try:
        clean_text = song_text.replace('"', '').replace("'", '').strip()

        if ' by ' in clean_text:
            parts = clean_text.split(' by ', 1)
            song_title = parts[0].strip()
            artist = parts[1].strip()
            search_query = f"{artist} {song_title}"
        else:
            search_query = clean_text

        encoded_query = urllib.parse.quote_plus(search_query)
        youtube_url = f"https://www.youtube.com/results?search_query={encoded_query}"
        return youtube_url

    except Exception as e:
        print(f"Error creating Youtube URL: {e}")
        return f"https://www.youtube.com/results?search_query={song_text.replace(' ', '+')}"

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

💡 **Tip:** Use 'boo ask <question>' to ask specific questions about this video!"""
                if is_edit:
                    response += "\n\n✏️ *Summary generated from edited request*"
                if send_message_func:
                    await send_message_func(room_id, response)
            else:
                if send_message_func:
                    await send_message_func(room_id, f"{edit_prefix}❌ Failed to generate summary. Please try again later.")

        except Exception as e:
            print(f"Error in YouTube summary: {e}")
            if send_message_func:
                await send_message_func(room_id, f"{edit_prefix}❌ Error processing video: {str(e)}")

    async def handle_youtube_subs(self, room_id, url, is_edit=False, send_message_func=None, send_file_attachment_func=None):
        """Handle YouTube subtitle extraction command"""
        try:
            edit_prefix = "✏️ " if is_edit else ""

            if send_message_func:
                await send_message_func(room_id, f"{edit_prefix}📹 *Extracting closed captions from YouTube video...*")

            # Get video title
            title = await self.get_youtube_title(url)

            # Extract subtitles/closed captions
            subtitles = await self.extract_youtube_subtitles(url)

            if subtitles:
                # Create filename with video title (sanitized)
                safe_title = re.sub(r'[^\w\s-]', '', title).strip()
                safe_title = re.sub(r'[-\s]+', '_', safe_title)
                filename = f"{safe_title}_captions.txt"

                # Save to temp file
                with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8', suffix='.txt', prefix=safe_title) as temp_file:
                    temp_file.write(f"YouTube Video: {title}\n")
                    temp_file.write(f"URL: {url}\n")
                    temp_file.write("=" * 50 + "\n\n")
                    temp_file.write(subtitles)
                    temp_file_path = temp_file.name

                file_size = os.path.getsize(temp_file_path)

                # Send file as attachment
                if send_file_attachment_func:
                    await send_file_attachment_func(room_id, temp_file_path, f"Closed captions for: {title}")

                # Send confirmation message
                if send_message_func:
                    await send_message_func(room_id, f"{edit_prefix}✅ **Closed captions extracted and attached!**\n📄 File: `{os.path.basename(temp_file_path)}`\n💾 Size: {file_size:,} bytes\n🎬 Video: {title}")

                # Clean up local file after sending
                os.remove(temp_file_path)
                print(f"Cleaned up local file: {temp_file_path}")
            else:
                if send_message_func:
                    await send_message_func(room_id, f"{edit_prefix}❌ No closed captions found for this video.\n🎬 Video: {title}")

        except Exception as e:
            print(f"Error handling YouTube subs: {e}")
            if send_message_func:
                await send_message_func(room_id, f"{edit_prefix}❌ Error processing YouTube URL: {str(e)}")

    async def handle_youtube_question(self, room_id, question_part, is_edit=False, send_message_func=None, current_display_name="boo"):
        """Handle questions about YouTube videos"""
        try:
            # Check for required dependencies
            if not os.getenv("OPENROUTER_API_KEY"):
                if send_message_func:
                    await send_message_func(room_id, "❌ YouTube Q&A requires OPENROUTER_API_KEY in .env file")
                return

            edit_prefix = "✏️ " if is_edit else ""
            
            # Check if question includes a YouTube URL
            youtube_url = None
            question = question_part
            
            # Look for YouTube URLs in the question
            youtube_pattern = r'(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]+)'
            url_match = re.search(youtube_pattern, question_part)
            
            if url_match:
                # Extract URL and question
                youtube_url = question_part[:url_match.end()]
                question = question_part[url_match.end():].strip()
                
                if not question:
                    if send_message_func:
                        await send_message_func(room_id, f"{edit_prefix}❌ Please provide a question after the YouTube URL")
                    return
            else:
                # No URL provided, use most recent video for this room
                if room_id not in self.last_processed_video or not self.last_processed_video[room_id]:
                    if send_message_func:
                        await send_message_func(room_id, f"{edit_prefix}❌ No recent YouTube video found in this room. Please process a video first with '{current_display_name} summary <url>' or specify a URL in your question.")
                    return
                youtube_url = self.last_processed_video[room_id]

            # Get transcript from cache or extract it
            transcript_data = await self.get_or_extract_transcript(youtube_url, room_id, edit_prefix, send_message_func)
            
            if not transcript_data:
                return  # Error message already sent

            title, transcript = transcript_data

            if send_message_func:
                await send_message_func(room_id, f"{edit_prefix}🤔 Analyzing video transcript to answer your question...")

            # Generate answer using AI
            answer = await self.answer_youtube_question(question, transcript, title)

            if answer:
                response = f"""{edit_prefix}💬 **Question about: {title}**

**Q:** {question}

**A:** {answer}"""
                if send_message_func:
                    await send_message_func(room_id, response)
            else:
                if send_message_func:
                    await send_message_func(room_id, f"{edit_prefix}❌ Failed to generate answer. Please try again later.")

        except Exception as e:
            print(f"Error in YouTube question handling: {e}")
            if send_message_func:
                await send_message_func(room_id, f"{edit_prefix}❌ Error processing question: {str(e)}")

    async def handle_list_videos(self, room_id, is_edit=False, send_message_func=None, current_display_name="boo"):
        """List recently processed YouTube videos for this room"""
        edit_prefix = "✏️ " if is_edit else ""
        
        # Get cache for this room
        room_cache = self.transcript_cache.get(room_id, {})
        
        if not room_cache:
            if send_message_func:
                await send_message_func(room_id, f"{edit_prefix}📹 No YouTube videos have been processed in this room yet.")
            return

        video_list = f"{edit_prefix}📹 **Recently Processed Videos (This Room):**\n\n"
        
        for i, (url, (title, _, timestamp)) in enumerate(room_cache.items(), 1):
            # Truncate title if too long
            display_title = title[:60] + "..." if len(title) > 60 else title
            recent_marker = " 🔄" if url == self.last_processed_video.get(room_id) else ""
            video_list += f"{i}. **{display_title}**{recent_marker}\n   `{url}`\n\n"

        video_list += f"💡 Use '{current_display_name} ask <question>' to ask about the most recent video{' 🔄' if self.last_processed_video.get(room_id) else ''}"
        
        if send_message_func:
            await send_message_func(room_id, video_list)

    async def extract_youtube_subtitles(self, url):
        """Extract subtitles from YouTube video using yt-dlp"""
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                # Run yt-dlp to extract subtitles
                cmd = [
                    'yt-dlp',
                    '--write-subs',
                    '--write-auto-subs',
                    '--sub-lang', 'en',
                    '--sub-format', 'vtt',
                    '--skip-download',
                    '--output', f'{temp_dir}/%(title)s.%(ext)s',
                    url
                ]

                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

                if result.returncode != 0:
                    print(f"yt-dlp error: {result.stderr}")
                    return None

                # Find and read the subtitle file
                for file in os.listdir(temp_dir):
                    if file.endswith('.vtt'):
                        with open(os.path.join(temp_dir, file), 'r', encoding='utf-8') as f:
                            vtt_content = f.read()
                            return self.parse_vtt(vtt_content)

                return None

        except subprocess.TimeoutExpired:
            print("yt-dlp timeout")
            return None
        except Exception as e:
            print(f"Error extracting subtitles: {e}")
            return None

    async def get_youtube_title(self, url):
        """Get YouTube video title using yt-dlp"""
        try:
            cmd = [
                'yt-dlp',
                '--get-title',
                url
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                return result.stdout.strip()
            else:
                return "YouTube Video"

        except Exception as e:
            print(f"Error getting title: {e}")
            return "YouTube Video"

    def parse_vtt(self, vtt_content):
        """Parse VTT subtitle content and extract text"""
        lines = vtt_content.split('\n')
        text_lines = []

        for line in lines:
            line = line.strip()
            # Skip VTT headers, timestamps, and empty lines
            if (line and
                not line.startswith('WEBVTT') and
                not line.startswith('NOTE') and
                not '-->' in line and
                not line.isdigit() and
                not re.match(r'^\d{2}:\d{2}:\d{2}', line)):

                # Remove HTML tags and clean up
                clean_line = re.sub(r'<[^>]+>', '', line)
                clean_line = re.sub(r'&\w+;', '', clean_line)  # Remove HTML entities

                if clean_line:
                    text_lines.append(clean_line)

        return ' '.join(text_lines)

    async def get_or_extract_transcript(self, youtube_url, room_id, edit_prefix, send_message_func=None) -> Optional[Tuple[str, str]]:
        """Get transcript from cache or extract it if not cached"""
        # Check cache for this room first
        room_cache = self.transcript_cache.get(room_id, {})
        
        if youtube_url in room_cache:
            print(f"📋 Using cached transcript for {youtube_url} in room {room_id}")
            title, transcript, _ = room_cache[youtube_url]
            return (title, transcript)

        # Not in cache, extract it
        if send_message_func:
            await send_message_func(room_id, f"{edit_prefix}📥 Video not in cache, extracting transcript...")
        
        title = await self.get_youtube_title(youtube_url)
        transcript = await self.extract_youtube_subtitles(youtube_url)

        if not transcript:
            if send_message_func:
                await send_message_func(room_id, f"{edit_prefix}❌ Could not extract transcript from video. The video might not have subtitles.")
            return None

        # Cache the transcript for this room
        self.cache_transcript(youtube_url, title, transcript, room_id)
        
        return (title, transcript)

    def cache_transcript(self, url: str, title: str, transcript: str, room_id: str):
        """Cache a transcript with size management (per room)"""
        # Initialize room cache if it doesn't exist
        if room_id not in self.transcript_cache:
            self.transcript_cache[room_id] = OrderedDict()
        
        room_cache = self.transcript_cache[room_id]
        
        # Remove oldest entries if room cache is full
        while len(room_cache) >= self.max_cached_transcripts_per_room:
            oldest_url = next(iter(room_cache))
            del room_cache[oldest_url]
            print(f"🗑️ Removed oldest cached transcript from room {room_id}: {oldest_url}")

        # Add new transcript to room cache
        room_cache[url] = (title, transcript, datetime.now())
        
        # Update last processed video for this room
        self.last_processed_video[room_id] = url
        
        print(f"📋 Cached transcript for room {room_id}: {title}")
        print(f"📊 Room {room_id} cache now contains {len(room_cache)} transcripts")

    async def answer_youtube_question(self, question: str, transcript: str, title: str) -> Optional[str]:
        """Use AI to answer a question about a YouTube video transcript with chunking support"""
        try:
            openrouter_key = os.getenv("OPENROUTER_API_KEY")
            if not openrouter_key:
                return None

            # Check if we need to use chunking for large transcripts
            max_direct_chars = 10000  # Direct processing limit for Q&A
            if len(transcript) > max_direct_chars:
                print(f"📏 Transcript too large for Q&A ({len(transcript)} chars), using chunking approach...")
                return await self.answer_question_large_transcript(question, transcript, title)
            
            # Standard single-pass Q&A for smaller transcripts
            return await self.answer_question_with_ai(question, transcript, title, is_chunk=False)

        except Exception as e:
            print(f"Error in AI question answering: {e}")
            return None

    async def answer_question_with_ai(self, question: str, transcript: str, title: str, is_chunk=False, is_final_combination=False) -> Optional[str]:
        """Core method to answer questions using AI with different contexts"""
        try:
            openrouter_key = os.getenv("OPENROUTER_API_KEY")
            if not openrouter_key:
                return None

            # Prepare different prompts based on context
            if is_final_combination:
                prompt = f"""You are combining answers from multiple parts of a YouTube video transcript to provide a comprehensive final answer.

Video Title: {title}
User Question: {question}

Partial Answers from Different Sections:
{transcript}

Please create a comprehensive, coherent answer that:
1. Combines relevant information from all sections
2. Removes redundancy and contradictions
3. Provides a clear, complete answer to the user's question
4. Indicates if some sections didn't contain relevant information
5. Cites specific details when available

Final Answer:"""

            elif is_chunk:
                prompt = f"""You are analyzing one section of a longer YouTube video transcript to find information relevant to a user's question.

Video Title: {title}
User Question: {question}

Transcript Section:
{transcript}

Please analyze this section and provide:
1. Any information that directly answers or relates to the user's question
2. Relevant details, examples, or quotes from this section
3. If this section doesn't contain relevant information, clearly state that
4. Be specific about what information comes from this particular section

Section Analysis:"""

            else:
                # Standard single-pass Q&A
                prompt = f"""You are answering a question about a YouTube video based on its transcript. Be accurate and only use information from the transcript provided.

Video Title: {title}

User Question: {question}

Video Transcript:
{transcript}

Please answer the user's question based ONLY on the information available in this transcript. If the transcript doesn't contain the information needed to answer the question, say so clearly. Be specific and cite relevant parts of the transcript when possible.

Answer:"""

            payload = {
                "model": "meta-llama/llama-3.2-3b-instruct:free",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": 500 if is_final_combination else 300,
                "temperature": 0.2  # Lower temperature for more factual responses
            }

            headers = {
                "Authorization": f"Bearer {openrouter_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/matrix-nio/matrix-nio",
                "X-Title": "Matrix Bot"
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:

                    if response.status == 200:
                        data = await response.json()
                        return data['choices'][0]['message']['content'].strip()
                    else:
                        error_text = await response.text()
                        print(f"OpenRouter API error {response.status}: {error_text}")
                        return None

        except Exception as e:
            print(f"Error in AI question answering: {e}")
            return None

    async def answer_question_large_transcript(self, question: str, transcript: str, title: str) -> Optional[str]:
        """
        Answer questions about large transcripts using hierarchical chunking approach.
        Returns a comprehensive answer that searches through all relevant parts.
        """
        try:
            print(f"📊 Processing large transcript for Q&A: {len(transcript)} characters")
            
            # Step 1: Chunk the transcript using the same method as summarization
            chunks = self.chunk_transcript_by_sentences(transcript)
            
            if len(chunks) <= 1:
                # Small enough for direct processing
                return await self.answer_question_with_ai(question, transcript, title, is_chunk=False)
            
            print(f"🔄 Analyzing {len(chunks)} chunks for relevant information...")
            
            # Step 2: Analyze each chunk for relevant information
            chunk_answers = []
            relevant_chunks = 0
            
            for i, chunk in enumerate(chunks):
                print(f"🔍 Analyzing chunk {i+1}/{len(chunks)} for question relevance...")
                
                chunk_answer = await self.answer_question_with_ai(
                    question,
                    chunk,
                    f"{title} (Part {i+1}/{len(chunks)})",
                    is_chunk=True
                )
                
                if chunk_answer and not chunk_answer.lower().startswith("this section doesn't contain"):
                    chunk_answers.append(f"**Part {i+1}:** {chunk_answer}")
                    relevant_chunks += 1
                
            if not chunk_answers:
                return f"Based on my analysis of the transcript, I couldn't find information that directly answers your question about '{question}'. The video content may not cover this topic in detail."
            
            # Step 3: Combine relevant chunk answers into final comprehensive answer
            print(f"🔗 Combining answers from {relevant_chunks} relevant chunks...")
            
            combined_text = "\n\n".join(chunk_answers)
            final_answer = await self.answer_question_with_ai(
                question,
                combined_text,
                title,
                is_final_combination=True
            )
            
            if final_answer:
                return final_answer
            else:
                # Fallback: return combined chunk answers
                return f"**Answer based on analysis of {relevant_chunks} relevant sections:**\n\n" + combined_text
                
        except Exception as e:
            print(f"❌ Error in large transcript Q&A: {e}")
            # Fallback to truncated Q&A
            return await self.answer_question_with_ai(question, transcript[:10000], title)

    async def summarize_with_ai(self, text, title="", is_chunk=False, is_final_combination=False):
        """Summarize text using OpenRouter AI"""
        try:
            openrouter_key = os.getenv("OPENROUTER_API_KEY")
            if not openrouter_key:
                print("Warning: OPENROUTER_API_KEY not found in .env file")
                return None

            # Check if we need to use chunking for large transcripts
            max_direct_chars = 12000  # Direct processing limit
            if len(text) > max_direct_chars and not is_chunk and not is_final_combination:
                print(f"📏 Transcript too large ({len(text)} chars), using chunking approach...")
                return await self.summarize_large_transcript(text, title)
            
            # Prepare different prompts based on context
            if is_final_combination:
                prompt = f"""You are combining multiple part summaries of a YouTube video into one comprehensive final summary.

Video Title: {title}

Part Summaries to Combine:
{text}

Please create a cohesive, comprehensive summary that:
1. Starts with the main points and key takeaways
2. Includes important details from all parts
3. Maintains logical flow and removes redundancy
4. Preserves specific examples, numbers, or quotes mentioned
5. Organizes information thematically rather than by parts

Provide a well-structured final summary:"""

            elif is_chunk:
                prompt = f"""You are summarizing one part of a longer YouTube video transcript. Focus on capturing the key points from this section while preserving important details.

Video Title: {title}

Transcript Section:
{text}

Please provide a detailed summary of this section that:
1. Captures all main points discussed
2. Includes specific details, examples, or numbers mentioned
3. Maintains the logical flow of ideas
4. Preserves context for later combination with other parts

Section summary:"""

            else:
                # Standard single-pass summary
                if len(text) > max_direct_chars:
                    text = text[:max_direct_chars] + "..."
                
                prompt = f"""Please provide a complete summary of this YouTube video transcript. Focus on the main points and key takeaways at the start and have the nuanced details at the end.

Title: {title}

Transcript:
{text}

Please provide a well-structured and complete summary."""

            payload = {
                "model": "meta-llama/llama-3.2-3b-instruct:free",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": 600 if is_final_combination else 400,
                "temperature": 0.2 if is_final_combination else 0.3
            }

            headers = {
                "Authorization": f"Bearer {openrouter_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/matrix-nio/matrix-nio",
                "X-Title": "Matrix Bot"
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:

                    if response.status == 200:
                        data = await response.json()
                        return data['choices'][0]['message']['content'].strip()
                    else:
                        error_text = await response.text()
                        print(f"OpenRouter API error {response.status}: {error_text}")
                        return None

        except Exception as e:
            print(f"Error in AI summarization: {e}")
            return None

    def chunk_transcript_by_sentences(self, text):
        """
        Intelligently chunk transcript by sentences with overlap.
        Returns list of chunks that respect sentence boundaries.
        """
        try:
            import re
            
            # First, split into sentences (improved regex)
            sentence_pattern = r'(?<=[.!?])\s+(?=[A-Z])'
            sentences = re.split(sentence_pattern, text.strip())
            
            # Clean up sentences and remove very short ones
            clean_sentences = []
            for sentence in sentences:
                sentence = sentence.strip()
                if len(sentence) > 10:  # Filter out very short fragments
                    clean_sentences.append(sentence)
            
            if not clean_sentences:
                # Fallback: split by periods if sentence detection fails
                clean_sentences = [s.strip() for s in text.split('.') if len(s.strip()) > 10]
            
            chunks = []
            current_chunk = ""
            current_sentences = []
            
            for sentence in clean_sentences:
                # Check if adding this sentence would exceed chunk size
                test_chunk = current_chunk + " " + sentence if current_chunk else sentence
                
                if len(test_chunk) <= self.chunk_size:
                    current_chunk = test_chunk
                    current_sentences.append(sentence)
                else:
                    # Current chunk is full, save it and start new one
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    
                    # Start new chunk with overlap from previous chunk
                    overlap_sentences = current_sentences[-3:] if len(current_sentences) >= 3 else current_sentences
                    current_chunk = " ".join(overlap_sentences + [sentence])
                    current_sentences = overlap_sentences + [sentence]
                    
                    # If single sentence is too long, split it
                    if len(current_chunk) > self.chunk_size:
                        # Force split the long sentence
                        words = sentence.split()
                        chunk_words = []
                        current_length = len(" ".join(overlap_sentences)) if overlap_sentences else 0
                        
                        for word in words:
                            test_length = current_length + len(" ".join(chunk_words + [word]))
                            if test_length <= self.chunk_size:
                                chunk_words.append(word)
                            else:
                                # Save current chunk and start new one
                                if chunk_words:
                                    chunk_text = " ".join(overlap_sentences + chunk_words) if overlap_sentences else " ".join(chunk_words)
                                    chunks.append(chunk_text.strip())
                                    chunk_words = [word]
                                    current_length = 0
                                    overlap_sentences = []
                                else:
                                    # Single word is too long, include it anyway
                                    chunk_words = [word]
                        
                        # Update current state
                        current_chunk = " ".join(chunk_words)
                        current_sentences = chunk_words  # Treat words as sentences for this case
            
            # Add the final chunk
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
            
            # Limit number of chunks to avoid overwhelming the AI
            if len(chunks) > self.max_chunks:
                print(f"⚠️ Transcript has {len(chunks)} chunks, limiting to {self.max_chunks}")
                # Take chunks evenly distributed across the transcript
                step = len(chunks) // self.max_chunks
                chunks = [chunks[i * step] for i in range(self.max_chunks)]
            
            print(f"📄 Split transcript into {len(chunks)} chunks (avg {sum(len(c) for c in chunks) // len(chunks)} chars each)")
            return chunks
            
        except Exception as e:
            print(f"❌ Error chunking transcript: {e}")
            # Fallback: simple character-based chunking
            chunks = []
            for i in range(0, len(text), self.chunk_size - self.chunk_overlap):
                chunk = text[i:i + self.chunk_size]
                chunks.append(chunk)
                if len(chunks) >= self.max_chunks:
                    break
            return chunks

    async def summarize_large_transcript(self, text, title=""):
        """
        Summarize large transcripts using hierarchical chunking approach.
        Returns a comprehensive summary that preserves important details.
        """
        try:
            print(f"📊 Processing large transcript: {len(text)} characters")
            
            # Step 1: Chunk the transcript
            chunks = self.chunk_transcript_by_sentences(text)
            
            if len(chunks) <= 1:
                # Small enough for direct processing
                return await self.summarize_with_ai(text, title, is_chunk=False)
            
            print(f"🔄 Processing {len(chunks)} chunks...")
            
            # Step 2: Summarize each chunk
            chunk_summaries = []
            for i, chunk in enumerate(chunks):
                print(f"📝 Summarizing chunk {i+1}/{len(chunks)}...")
                
                chunk_summary = await self.summarize_with_ai(
                    chunk,
                    f"{title} (Part {i+1}/{len(chunks)})",
                    is_chunk=True
                )
                
                if chunk_summary:
                    chunk_summaries.append(f"**Part {i+1}:** {chunk_summary}")
                else:
                    print(f"⚠️ Failed to summarize chunk {i+1}")
            
            if not chunk_summaries:
                return "❌ Failed to summarize any chunks of the transcript."
            
            # Step 3: Combine chunk summaries into final summary
            print(f"🔗 Combining {len(chunk_summaries)} chunk summaries...")
            
            combined_text = "\n\n".join(chunk_summaries)
            final_summary = await self.summarize_with_ai(
                combined_text,
                title,
                is_final_combination=True
            )
            
            if final_summary:
                return final_summary
            else:
                # Fallback: return combined chunk summaries
                return f"**Comprehensive Summary (from {len(chunks)} parts):**\n\n" + combined_text
                
        except Exception as e:
            print(f"❌ Error in large transcript summarization: {e}")
            # Fallback to truncated summary
            return await self.summarize_with_ai(text[:12000], title)
import yt_dlp
import os
import tempfile
import logging
import urllib.parse

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
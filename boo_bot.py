#!/usr/bin/env python3
"""
Matrix Chatbot with Enhanced Media Message Detection 
"""

print("🚀 Starting Simplified Matrix Bot with Enhanced Media Detection, NIST Beacon, and YouTube Features...")

# Add debug imports with error handling
try:
    import asyncio
    import json
    import os
    import re
    import io
    import tempfile
    import subprocess
    from datetime import datetime
    from pathlib import Path
    from collections import OrderedDict
    from typing import Dict, Optional, Tuple
    print("✅ Standard library modules imported successfully")
except ImportError as e:
    print(f"❌ Failed to import standard library modules: {e}")
    exit(1)

try:
    from dotenv import load_dotenv
    print("✅ dotenv imported successfully")
except ImportError as e:
    print(f"❌ Failed to import dotenv: {e}")
    print("Install with: pip install python-dotenv")
    exit(1)

try:
    from nio import (
        AsyncClient, MatrixRoom, RoomMessageText, RoomMessageMedia,
        RoomMessageImage, RoomMessageFile, RoomMessageAudio, RoomMessageVideo,
        LoginResponse, KeysUploadResponse, KeysQueryResponse, RoomMessage,
        Event
    )
    from nio.crypto import Olm
    from nio.exceptions import OlmUnverifiedDeviceError
    from nio.events import MegolmEvent

    # Import encrypted media event types
    try:
        from nio.events.room_events import (
            RoomEncryptedImage, RoomEncryptedVideo, RoomEncryptedAudio, RoomEncryptedFile
        )
        ENCRYPTED_EVENTS_AVAILABLE = True
        print("✅ matrix-nio with encrypted events imported successfully")
    except ImportError:
        ENCRYPTED_EVENTS_AVAILABLE = False
        print("⚠️ Encrypted media events not available - will use fallback detection")

    print("✅ matrix-nio imported successfully")
except ImportError as e:
    print(f"❌ Failed to import matrix-nio: {e}")
    print("Install with: pip install matrix-nio")
    exit(1)

# Try to import our database client with better error handling
try:
    from api_client import ChatDatabaseClient
    print("✅ ChatDatabaseClient imported successfully")
    DATABASE_CLIENT_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Warning: Could not import ChatDatabaseClient: {e}")
    print("Database features will be disabled. Make sure api_client.py exists in the same directory.")
    DATABASE_CLIENT_AVAILABLE = False

    # Create a dummy class so the code doesn't crash
    class ChatDatabaseClient:
        def __init__(self, *args, **kwargs):
            pass

try:
    import aiohttp
    import aiofiles
    AIOHTTP_AVAILABLE = True
    print("✅ aiohttp and aiofiles imported successfully")
except ImportError:
    AIOHTTP_AVAILABLE = False
    print("⚠️ Warning: aiohttp/aiofiles not installed. Media download and NIST/AI/YouTube features will be disabled.")

try:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.backends import default_backend
    import base64
    import hashlib
    CRYPTO_AVAILABLE = True
    print("✅ cryptography library available for media decryption")
except ImportError:
    CRYPTO_AVAILABLE = False
    print("⚠️ Warning: cryptography library not installed. Manual decryption will be disabled.")
    print("   Install with: pip install cryptography")

# Force load .env from current directory
load_dotenv('./.env')
print(f"🔧 EXPLICIT CHECK - DATABASE_API_KEY: {os.getenv('DATABASE_API_KEY')}")
print(f"🔧 EXPLICIT CHECK - DATABASE_API_URL: {os.getenv('DATABASE_API_URL')}")

class DebugMatrixBot:
    def __init__(self, homeserver, user_id, password, device_name="SimplifiedChatBot"):
        print(f"🤖 Initializing Simplified MatrixBot...")
        print(f"   Homeserver: {homeserver}")
        print(f"   User ID: {user_id}")
        print(f"   Device: {device_name}")

        self.homeserver = homeserver
        self.user_id = user_id
        self.password = password
        self.device_name = device_name

        # Store path for encryption keys
        self.store_path = "./bot_store"

        # Ensure store directory exists
        os.makedirs(self.store_path, exist_ok=True)
        print(f"✅ Bot store directory ready: {self.store_path}")

        # Create temp directory for media downloads
        self.temp_media_dir = "./temp_media"
        os.makedirs(self.temp_media_dir, exist_ok=True)
        print(f"✅ Temporary media directory ready: {self.temp_media_dir}")

        # Counters for debugging
        self.event_counters = {
            'text_messages': 0,
            'media_messages': 0,
            'unknown_events': 0,
            'encrypted_events': 0,
            'decryption_failures': 0
        }

        # YouTube Q&A functionality (per-room)
        self.transcript_cache = {}  # room_id -> OrderedDict of URL -> (title, transcript, timestamp)
        self.max_cached_transcripts_per_room = 5  # Limit memory usage per room
        self.last_processed_video = {}  # room_id -> most recent video URL

        # Chunking configuration for large transcripts
        self.chunk_size = 8000  # Characters per chunk (conservative for token limits)
        self.chunk_overlap = 800  # Overlap between chunks to maintain context
        self.max_chunks = 10  # Maximum number of chunks to process

        # Dynamic bot name handling
        self.current_display_name = None  # No fallback
        self.last_name_check = None  # Track when we last checked the name

        # Initialize client with store path
        try:
            self.client = AsyncClient(homeserver, user_id, store_path=self.store_path)
            print("✅ AsyncClient initialized successfully")
        except Exception as e:
            print(f"❌ Failed to initialize AsyncClient: {e}")
            raise

        # Initialize database client
        self.db_client = None
        self.db_enabled = False
        if DATABASE_CLIENT_AVAILABLE:
            self._init_database_client()
        else:
            print("⚠️ Database client not available - skipping initialization")

        # Add event callbacks for ALL message types + debugging
        try:
            # Text messages
            self.client.add_event_callback(self.text_message_callback, RoomMessageText)

            # Regular (unencrypted) media messages
            self.client.add_event_callback(self.media_message_callback, RoomMessageImage)
            self.client.add_event_callback(self.media_message_callback, RoomMessageFile)
            self.client.add_event_callback(self.media_message_callback, RoomMessageAudio)
            self.client.add_event_callback(self.media_message_callback, RoomMessageVideo)

            # Encrypted media messages
            if ENCRYPTED_EVENTS_AVAILABLE:
                self.client.add_event_callback(self.encrypted_media_message_callback, RoomEncryptedImage)
                self.client.add_event_callback(self.encrypted_media_message_callback, RoomEncryptedVideo)
                self.client.add_event_callback(self.encrypted_media_message_callback, RoomEncryptedAudio)
                self.client.add_event_callback(self.encrypted_media_message_callback, RoomEncryptedFile)
                print("✅ Encrypted media callbacks registered!")
            else:
                print("⚠️ Encrypted media callbacks not available - using fallback")

            # General message callback to catch anything we might miss
            self.client.add_event_callback(self.general_message_callback, RoomMessage)

            # Decryption issues
            self.client.add_event_callback(self.decryption_failure_callback, MegolmEvent)

            # Catch ALL events for debugging
            self.client.add_event_callback(self.debug_all_events_callback, Event)

            print("✅ Event callbacks registered successfully (text + media + encrypted + debug)")
        except Exception as e:
            print(f"❌ Failed to register event callbacks: {e}")
            raise

    def _init_database_client(self):
        """Initialize the database client if API credentials are available"""
        try:
            api_url = os.getenv("DATABASE_API_URL")
            api_key = os.getenv("DATABASE_API_KEY")

            print(f"🔧 Database API URL: {api_url}")
            print(f"🔧 Database API Key: {'*' * 10 if api_key else 'Not set'}")

            if api_url and api_key:
                self.db_client = ChatDatabaseClient(api_url, api_key)
                self.db_enabled = True
                print(f"✅ Database client initialized: {api_url}")
            else:
                print("⚠️ Database API credentials not found in .env - database features disabled")
                print("   Add DATABASE_API_URL and DATABASE_API_KEY to enable database storage")
        except Exception as e:
            print(f"❌ Error initializing database client: {e}")
            self.db_enabled = False

    async def debug_all_events_callback(self, room: MatrixRoom, event: Event):
        """Catch and log ALL events for debugging purposes"""
        try:
            event_type = type(event).__name__

            # Skip our own messages and very frequent events
            if event.sender == self.user_id:
                return

            # Log interesting events
            if 'Message' in event_type or 'Media' in event_type or 'Encrypted' in event_type:
                print(f"🔍 DEBUG - All Events: {event_type} from {event.sender}")
                print(f"🔍 DEBUG - Event details: {event}")

                if hasattr(event, 'content'):
                    print(f"🔍 DEBUG - Event content: {event.content}")

        except Exception as e:
            print(f"❌ Error in debug_all_events_callback: {e}")

    async def get_bot_display_name(self):
        """Get the bot's current display name from Matrix (no fallback)"""
        try:
            # Get the bot's profile from Matrix
            response = await self.client.get_displayname(self.user_id)
            if hasattr(response, 'displayname') and response.displayname:
                display_name = response.displayname.strip()
                print(f"🤖 Bot display name retrieved: '{display_name}'")
                return display_name
            else:
                print(f"⚠️ No display name set for bot user {self.user_id}")
                return None
        except Exception as e:
            print(f"❌ Error getting display name: {e}")
            return None

    async def update_command_prefix(self):
        """Update the command prefix based on current display name"""
        try:
            display_name = await self.get_bot_display_name()
            if display_name:
                # Store the display name and create command prefix with colon
                self.current_display_name = display_name
                print(f"✅ Bot display name updated to: '{self.current_display_name}'")
                print(f"✅ Bot will respond to commands like: '{self.current_display_name}: help'")
                return True
            else:
                print(f"❌ Could not retrieve display name - bot commands disabled")
                self.current_display_name = None
                return False
        except Exception as e:
            print(f"❌ Error updating command prefix: {e}")
            self.current_display_name = None
            return False

    async def general_message_callback(self, room: MatrixRoom, event: RoomMessage):
        """Catch all room messages to see what we might be missing"""
        try:
            # Skip our own messages
            if event.sender == self.user_id:
                return

            event_type = type(event).__name__

            print(f"🔍 GENERAL MESSAGE CALLBACK: {event_type}")
            print(f"🔍   From: {event.sender}")
            print(f"🔍   Event ID: {event.event_id}")
            print(f"🔍   Encrypted: {event.decrypted}")

            if hasattr(event, 'body'):
                print(f"🔍   Body: {event.body}")

            if hasattr(event, 'url'):
                print(f"🔍   Media URL: {event.url}")

            if hasattr(event, 'mimetype'):
                print(f"🔍   MIME Type: {event.mimetype}")

            # Store in database with generic handling
            await self.store_message_in_db(
                room_id=room.room_id,
                event_id=event.event_id,
                sender=event.sender,
                message_type=event_type.lower().replace('roommessage', ''),
                content=getattr(event, 'body', str(event)),
                timestamp=datetime.fromtimestamp(event.server_timestamp / 1000)
            )

        except Exception as e:
            print(f"❌ Error in general_message_callback: {e}")
            import traceback
            traceback.print_exc()

    async def store_message_in_db(self, room_id, event_id, sender, message_type, content=None, timestamp=None):
        """Store a message in the database (with error handling)"""
        if not self.db_enabled or not self.db_client:
            print(f"📁 Skipping DB storage - DB not enabled")
            return None

        try:
            print(f"📁 Storing in DB: {message_type} from {sender}")

            result = await self.db_client.store_message(
                room_id=room_id,
                event_id=event_id,
                sender=sender,
                message_type=message_type,
                content=content,
                timestamp=timestamp or datetime.now()
            )

            if result:
                print(f"📁 ✅ Stored message in database: ID {result.get('id', 'unknown')}")
            else:
                print("⚠️ Failed to store message in database")

            return result

        except Exception as e:
            print(f"❌ Database storage error: {e}")
            import traceback
            traceback.print_exc()
            return None

    async def download_matrix_media(self, mxc_url, filename=None, encryption_info=None, original_mimetype=None):
        """Download and decrypt media from Matrix server with extensive debugging"""
        if not AIOHTTP_AVAILABLE:
            print("❌ Cannot download media - aiohttp not available")
            return None

        try:
            print(f"📥 Starting media download:")
            print(f"📥   MXC URL: {mxc_url}")
            print(f"📥   Filename: {filename}")
            print(f"📥   Original MIME Type: {original_mimetype}")
            print(f"📥   Has encryption info: {encryption_info is not None}")

            # Parse MXC URL (format: mxc://server/media_id)
            if not mxc_url.startswith("mxc://"):
                print(f"❌ Invalid MXC URL: {mxc_url}")
                return None

            # Download the media using matrix-nio's download method
            print(f"📥 Calling client.download()...")
            response = await self.client.download(mxc_url)

            print(f"📥 Download response type: {type(response)}")
            print(f"📥 Download response: {response}")

            if hasattr(response, 'body'):
                print(f"📥 ✅ Download successful - body size: {len(response.body)} bytes")

                # Check if we need to decrypt the content
                decrypted_data = response.body
                if encryption_info:
                    print(f"🔓 Attempting to decrypt media content...")
                    try:
                        # First try to decrypt using nio's crypto functions
                        from nio.crypto.attachments import decrypt_attachment

                        # Extract the actual base64 key string from the key dict
                        key_data = encryption_info.get('key', {})
                        if isinstance(key_data, dict):
                            key_b64 = key_data.get('k', '')
                            print(f"🔓 Extracted base64 key from dict: {key_b64[:10]}...")
                        else:
                            key_b64 = str(key_data)
                            print(f"🔓 Using key as string: {key_b64[:10]}...")

                        iv_b64 = encryption_info.get('iv', '')
                        hashes_data = encryption_info.get('hashes', {})
                        if isinstance(hashes_data, dict):
                            expected_hash = hashes_data.get('sha256', '')
                        else:
                            expected_hash = str(hashes_data)

                        print(f"🔓 Decryption parameters:")
                        print(f"🔓   Key (base64): {key_b64[:20]}...")
                        print(f"🔓   IV (base64): {iv_b64}")
                        print(f"🔓   Expected hash: {expected_hash[:20]}...")

                        # Use matrix-nio's decrypt_attachment with corrected parameters
                        decrypted_data = decrypt_attachment(
                            ciphertext=response.body,
                            key=key_b64,  # Pass the base64 string, not the dict
                            hash=expected_hash,
                            iv=iv_b64
                        )
                        print(f"🔓 ✅ Successfully decrypted media using nio - size: {len(decrypted_data)} bytes")

                    except ImportError:
                        print(f"⚠️ decrypt_attachment not available - trying alternative method")
                        if not CRYPTO_AVAILABLE:
                            print(f"❌ cryptography library not available - cannot decrypt")
                            print(f"💡 Install with: pip install cryptography")
                        else:
                            try:
                                # Alternative decryption method using base crypto
                                print(f"🔓 Using manual decryption...")

                                # Extract encryption parameters
                                key_data = encryption_info.get('key', {})
                                if isinstance(key_data, dict):
                                    key_b64 = key_data.get('k', '')
                                else:
                                    key_b64 = str(key_data)

                                iv_b64 = encryption_info.get('iv', '')
                                hashes_data = encryption_info.get('hashes', {})
                                if isinstance(hashes_data, dict):
                                    expected_hash = hashes_data.get('sha256', '')
                                else:
                                    expected_hash = str(hashes_data)

                                print(f"🔓   Key (first 20 chars): {key_b64[:20]}...")
                                print(f"🔓   IV: {iv_b64}")
                                print(f"🔓   Expected hash: {expected_hash[:16]}...")

                                # Decode base64 parameters
                                key = base64.b64decode(key_b64)
                                iv = base64.b64decode(iv_b64)

                                # Decrypt using AES-CTR
                                cipher = Cipher(algorithms.AES(key), modes.CTR(iv), backend=default_backend())
                                decryptor = cipher.decryptor()
                                decrypted_data = decryptor.update(response.body) + decryptor.finalize()

                                # Verify hash if provided
                                if expected_hash:
                                    actual_hash = base64.b64encode(hashlib.sha256(decrypted_data).digest()).decode('utf-8')
                                    if actual_hash == expected_hash:
                                        print(f"🔓 ✅ Manual decryption successful and hash verified!")
                                    else:
                                        print(f"⚠️ Hash mismatch - decryption may have failed")
                                        print(f"     Expected: {expected_hash}")
                                        print(f"     Actual:   {actual_hash}")
                                else:
                                    print(f"🔓 ✅ Manual decryption completed (no hash to verify)")

                            except Exception as decrypt_error:
                                print(f"❌ Manual decryption failed: {decrypt_error}")
                                # Use original data if decryption fails
                                print(f"🔄 Using original encrypted data")
                                import traceback
                                traceback.print_exc()

                    except Exception as e:
                        print(f"❌ Decryption failed: {e}")
                        print(f"🔄 Using original encrypted data")
                        import traceback
                        traceback.print_exc()
                else:
                    print(f"📥 No encryption info provided - using downloaded data as-is")

                # Generate filename if not provided
                if not filename:
                    media_id = mxc_url.split('/')[-1]
                    # Use original MIME type to determine extension
                    if original_mimetype:
                        import mimetypes
                        ext = mimetypes.guess_extension(original_mimetype) or ""
                        filename = f"media_{media_id}{ext}"
                    else:
                        filename = f"media_{media_id}"

                # Save to temp directory
                filepath = Path(self.temp_media_dir) / filename

                async with aiofiles.open(filepath, 'wb') as f:
                    await f.write(decrypted_data)

                print(f"📥 ✅ Saved {'decrypted ' if encryption_info else ''}media to: {filepath}")
                print(f"📥 ✅ File size: {len(decrypted_data)} bytes")

                # Return both filepath and original MIME type for proper upload
                return str(filepath), original_mimetype
            else:
                print(f"❌ Download failed - no body in response: {response}")
                return None

        except Exception as e:
            print(f"❌ Error downloading media: {e}")
            import traceback
            traceback.print_exc()
            return None

    async def upload_media_to_db(self, message_id, file_path, original_mimetype=None):
        """Upload media file to database API with debugging and MIME type preservation"""
        if not self.db_enabled or not self.db_client:
            print(f"📤 Skipping media upload - DB not enabled")
            return None

        try:
            print(f"📤 Uploading media to database:")
            print(f"📤   Message ID: {message_id}")
            print(f"📤   File path: {file_path}")
            print(f"📤   Original MIME type: {original_mimetype}")

            # Use the standard upload method from the simplified API client
            result = await self.db_client.upload_media(message_id, file_path)

            if result:
                print(f"📤 ✅ Uploaded media to database: {result}")

                # Clean up temp file
                try:
                    os.unlink(file_path)
                    print(f"🗑️ Cleaned up temp file: {file_path}")
                except:
                    pass

            return result
        except Exception as e:
            print(f"❌ Error uploading media to database: {e}")
            import traceback
            traceback.print_exc()
            return None

    async def text_message_callback(self, room: MatrixRoom, event: RoomMessageText):
        """Handle incoming text messages and edits"""
        try:
            self.event_counters['text_messages'] += 1

            print(f"📨 TEXT MESSAGE #{self.event_counters['text_messages']}")
            print(f"📨   Room: {room.name}")
            print(f"📨   From: {event.sender}")
            print(f"📨   Content: {event.body}")
            print(f"📨   Encrypted: {event.decrypted}")

            # Store incoming message in database
            await self.store_message_in_db(
                room_id=room.room_id,
                event_id=event.event_id,
                sender=event.sender,
                message_type="text",
                content=event.body,
                timestamp=datetime.fromtimestamp(event.server_timestamp / 1000)
            )

            # Ignore our own messages
            if event.sender == self.user_id:
                return

            # Check if this is an edit - use both relates_to property and "* " prefix
            is_edit = (hasattr(event, 'relates_to') and event.relates_to) or event.body.startswith("* ")

            # Handle both original messages and edits
            message_body = event.body

            # Update command prefix periodically or on first run
            current_time = datetime.now()
            if (self.last_name_check is None or
                (current_time - self.last_name_check).seconds > 15):  # Check every 5 minutes
                await self.update_command_prefix()
                self.last_name_check = current_time
    
            # Only process commands if we have a valid display name
            if not self.current_display_name:
                print(f"🚫 Ignoring message - no valid display name set")
                return
    
            # Handle edit formatting - Matrix often prefixes edits with "* "
            # We need to check for bot commands in both the original and cleaned message
            original_message = message_body
            cleaned_message = message_body
            
            if message_body.startswith("* "):
                cleaned_message = message_body[2:].strip()
                print(f"🔍 Detected edit prefix, cleaned message: '{cleaned_message}'")
    
            # Check for bot commands using display name with colon format
            # Try both the original message and cleaned message for edits
            expected_prefix = f"{self.current_display_name.lower()}:"
            print(f"🔍 Looking for command prefix: '{expected_prefix}'")
            
            # Check cleaned message first (for edits)
            cleaned_lower = cleaned_message.lower().strip()
            original_lower = original_message.lower().strip()
            
            print(f"🔍 Cleaned message lower: '{cleaned_lower}'")
            print(f"🔍 Original message lower: '{original_lower}'")
            
            command_found = False
            command_to_process = None
            
            if cleaned_lower.startswith(expected_prefix):
                command_found = True
                command_to_process = cleaned_message
                print(f"🔍 Command found in cleaned message: '{command_to_process}'")
            elif original_lower.startswith(expected_prefix):
                command_found = True
                command_to_process = original_message
                print(f"🔍 Command found in original message: '{command_to_process}'")
            
            if command_found:
                if is_edit:
                    print(f"🤖 Responding to edited command with '{self.current_display_name}:': {command_to_process}")
                else:
                    print(f"🤖 Responding to command with '{self.current_display_name}:': {command_to_process}")
                await self.handle_bot_command(room, event, command_to_process)
            else:
                print(f"🔍 No command found. Expected: '{expected_prefix}', cleaned: '{cleaned_lower}', original: '{original_lower}'")

        except Exception as e:
            print(f"❌ Error in text message callback: {e}")
            import traceback
            traceback.print_exc()

    async def encrypted_media_message_callback(self, room: MatrixRoom, event):
        """Handle incoming ENCRYPTED media messages"""
        try:
            self.event_counters['media_messages'] += 1

            # Ignore our own messages
            if event.sender == self.user_id:
                print(f"📎🔐 Ignoring our own encrypted media message")
                return

            # Determine media type
            media_type = "unknown"
            if hasattr(event, '__class__'):
                class_name = event.__class__.__name__
                if "Image" in class_name:
                    media_type = "image"
                elif "File" in class_name:
                    media_type = "file"
                elif "Audio" in class_name:
                    media_type = "audio"
                elif "Video" in class_name:
                    media_type = "video"

            print(f"📎🔐 ENCRYPTED MEDIA MESSAGE #{self.event_counters['media_messages']} 🔒🎉")
            print(f"📎🔐   Room: {room.name}")
            print(f"📎🔐   From: {event.sender}")
            print(f"📎🔐   Type: {media_type}")
            print(f"📎🔐   Class: {type(event).__name__}")
            print(f"📎🔐   Decrypted: {event.decrypted}")
            print(f"📎🔐   Event ID: {event.event_id}")

            # Get media info with detailed logging
            media_url = getattr(event, 'url', None)
            filename = getattr(event, 'body', f"encrypted_media_{event.event_id}")
            mimetype = getattr(event, 'mimetype', None)

            print(f"📎🔐   Filename: {filename}")
            print(f"📎🔐   MXC URL: {media_url}")
            print(f"📎🔐   MIME Type: {mimetype}")

            # Extract encryption info properly
            encryption_info = None
            if hasattr(event, 'key') and hasattr(event, 'iv') and hasattr(event, 'hashes'):
                encryption_info = {
                    'key': event.key,  # This is already a dict with the 'k' field
                    'iv': event.iv,
                    'hashes': event.hashes
                }
                print(f"📎🔐   🔐 Extracted encryption info from event attributes")
                print(f"📎🔐   🔐 Key type: {type(event.key)}")
                print(f"📎🔐   🔐 Key preview: {str(event.key)[:50]}...")
            elif hasattr(event, 'file') and event.file:
                # Encryption info might be in the 'file' field
                file_info = event.file
                if isinstance(file_info, dict):
                    encryption_info = {
                        'key': file_info.get('key', {}),
                        'iv': file_info.get('iv'),
                        'hashes': file_info.get('hashes', {})
                    }
                    print(f"📎🔐   🔐 Extracted encryption info from file field")

            if encryption_info:
                print(f"📎🔐   🔐 Encryption info available: {encryption_info is not None}")
            else:
                print(f"📎🔐   ⚠️ No encryption info found!")

            # Store message in database first (without media file)
            print(f"📁🔐 Storing encrypted media message in database...")
            stored_message = await self.store_message_in_db(
                room_id=room.room_id,
                event_id=event.event_id,
                sender=event.sender,
                message_type=media_type,
                content=f"Encrypted media file: {filename}",
                timestamp=datetime.fromtimestamp(event.server_timestamp / 1000)
            )

            # Download and upload media if we have database storage enabled
            if self.db_enabled and media_url and stored_message:
                print(f"📥🔐 Starting encrypted media download process...")

                # Download with original MIME type
                download_result = await self.download_matrix_media(
                    media_url,
                    filename,
                    encryption_info,
                    original_mimetype=mimetype  # Pass the original MIME type
                )

                if download_result:
                    if isinstance(download_result, tuple):
                        local_file_path, original_mimetype = download_result
                    else:
                        local_file_path = download_result
                        original_mimetype = mimetype

                    # Upload to database
                    message_id = stored_message.get('id')
                    if message_id:
                        print(f"📤🔐 Uploading decrypted media to database (message ID: {message_id})...")
                        await self.upload_media_to_db(message_id, local_file_path, original_mimetype)
                    else:
                        print("⚠️🔐 No message ID returned, cannot upload media")
                        # Clean up temp file
                        try:
                            os.unlink(local_file_path)
                        except:
                            pass
                else:
                    print("❌🔐 Failed to download encrypted media file")
            else:
                if not self.db_enabled:
                    print("⚠️🔐 Database not enabled, skipping encrypted media upload")
                elif not media_url:
                    print("⚠️🔐 No media URL found in encrypted event")
                elif not stored_message:
                    print("⚠️🔐 Failed to store encrypted message, skipping media upload")

        except Exception as e:
            print(f"❌ Error in encrypted media message callback: {e}")
            import traceback
            traceback.print_exc()

    async def media_message_callback(self, room: MatrixRoom, event):
        """Handle incoming media messages with extensive debugging"""
        try:
            self.event_counters['media_messages'] += 1

            # Ignore our own messages
            if event.sender == self.user_id:
                print(f"📎 Ignoring our own media message")
                return

            # Determine media type
            media_type = "unknown"
            if hasattr(event, '__class__'):
                class_name = event.__class__.__name__
                if "Image" in class_name:
                    media_type = "image"
                elif "File" in class_name:
                    media_type = "file"
                elif "Audio" in class_name:
                    media_type = "audio"
                elif "Video" in class_name:
                    media_type = "video"

            print(f"📎 MEDIA MESSAGE #{self.event_counters['media_messages']} 🎉")
            print(f"📎   Room: {room.name}")
            print(f"📎   From: {event.sender}")
            print(f"📎   Type: {media_type}")
            print(f"📎   Class: {type(event).__name__}")
            print(f"📎   Encrypted: {event.decrypted}")
            print(f"📎   Event ID: {event.event_id}")

            # Get media info with detailed logging
            media_url = getattr(event, 'url', None)
            filename = getattr(event, 'body', f"media_{event.event_id}")
            mimetype = getattr(event, 'mimetype', None)

            print(f"📎   Filename: {filename}")
            print(f"📎   MXC URL: {media_url}")
            print(f"📎   MIME Type: {mimetype}")

            # Check for encryption
            if hasattr(event, 'file'):
                print(f"📎   🔐 ENCRYPTED MEDIA DETECTED!")
                print(f"📎   File object: {event.file}")

            # Store message in database first (without media file)
            print(f"📁 Storing media message in database...")
            stored_message = await self.store_message_in_db(
                room_id=room.room_id,
                event_id=event.event_id,
                sender=event.sender,
                message_type=media_type,
                content=f"Media file: {filename}",
                timestamp=datetime.fromtimestamp(event.server_timestamp / 1000)
            )

            # Download and upload media if we have database storage enabled
            if self.db_enabled and media_url and stored_message:
                print(f"📥 Starting media download process...")

                # Download the media file with original MIME type
                download_result = await self.download_matrix_media(
                    media_url,
                    filename,
                    encryption_info=None,
                    original_mimetype=mimetype
                )

                if download_result:
                    if isinstance(download_result, tuple):
                        local_file_path, original_mimetype = download_result
                    else:
                        local_file_path = download_result
                        original_mimetype = mimetype

                    # Upload to database
                    message_id = stored_message.get('id')
                    if message_id:
                        print(f"📤 Uploading media to database (message ID: {message_id})...")
                        await self.upload_media_to_db(message_id, local_file_path, original_mimetype)
                    else:
                        print("⚠️ No message ID returned, cannot upload media")
                        # Clean up temp file
                        try:
                            os.unlink(local_file_path)
                        except:
                            pass
                else:
                    print("❌ Failed to download media file")
            else:
                if not self.db_enabled:
                    print("⚠️ Database not enabled, skipping media upload")
                elif not media_url:
                    print("⚠️ No media URL found in event")
                elif not stored_message:
                    print("⚠️ Failed to store message, skipping media upload")

        except Exception as e:
            print(f"❌ Error in media message callback: {e}")
            import traceback
            traceback.print_exc()

    async def decryption_failure_callback(self, room: MatrixRoom, event: MegolmEvent):
        """Handle decryption failures by requesting keys"""
        self.event_counters['decryption_failures'] += 1
        print(f"🔓 DECRYPTION FAILURE #{self.event_counters['decryption_failures']}")
        print(f"🔓   Room: {room.name}")
        print(f"🔓   From: {event.sender}")
        print(f"🔓   Session ID: {event.session_id}")

        # Request missing keys
        try:
            await self.client.request_room_key(event)
            print(f"🔑 Requested room key for session {event.session_id}")
        except Exception as e:
            print(f"❌ Failed to request room key: {e}")

    async def handle_bot_command(self, room: MatrixRoom, event, command_text=None):
        """Handle bot commands with dynamic prefix and colon format"""
        try:
            command = command_text if command_text is not None else event.body.strip()
            command_lower = command.lower()

            is_edit = hasattr(event, 'relates_to') and event.relates_to
            edit_prefix = "[EDIT] " if is_edit else ""

            print(f"🤖 Processing command: {command}")

            # Skip processing if no display name is set
            if not self.current_display_name:
                await self.send_message(room.room_id, f"{edit_prefix}❌ Bot display name not configured. Please set a display name in Matrix.")
                return

            # Create the current command prefix for matching (with colon)
            prefix = f"{self.current_display_name.lower()}:"
            
            # Helper function to check if command matches a pattern
            def matches_command(pattern):
                expected = f"{prefix} {pattern}".strip()
                return command_lower == expected or command_lower.startswith(expected + " ")
            
            def matches_exact(pattern):
                expected = f"{prefix} {pattern}".strip()
                return command_lower == expected

            if matches_exact("debug"):
                debug_info = f"""{edit_prefix}🔍 **SIMPLIFIED DEBUG INFO**

📊 **Event Counters:**
• Text messages: {self.event_counters['text_messages']}
• Media messages: {self.event_counters['media_messages']}
• Unknown events: {self.event_counters['unknown_events']}
• Encrypted events: {self.event_counters['encrypted_events']}
• Decryption failures: {self.event_counters['decryption_failures']}

🤖 **Bot Identity:**
• Display name: {self.current_display_name}
• Command format: {self.current_display_name}: <command>

🔧 **Configuration:**
• Database enabled: {'✅ Yes' if self.db_enabled else '❌ No'}
• aiohttp available: {'✅ Yes' if AIOHTTP_AVAILABLE else '❌ No'}
• Cryptography library: {'✅ Yes' if CRYPTO_AVAILABLE else '❌ No'}
• Encrypted events support: {'✅ Yes' if ENCRYPTED_EVENTS_AVAILABLE else '❌ No'}
• Room encrypted: {'🔒 Yes' if room.encrypted else '🔓 No'}
• Store path: {self.store_path}
• Temp media dir: {self.temp_media_dir}

✅ **Simplified Features:**
• Media processing with MIME preservation
• NIST Beacon integration for randomness
• YouTube summary functionality
• Enhanced encrypted media decryption
"""

                await self.send_message(room.room_id, debug_info)

            elif matches_exact("talk"):
                await self.send_message(room.room_id, f"{edit_prefix}Hello! I'm {self.current_display_name} - the simplified bot with proper encrypted media decryption!")

            elif matches_exact("help"):
                help_text = f"""{edit_prefix}🔍 **{self.current_display_name.upper()} BOT Commands:**
• {self.current_display_name}: debug - Show debug information
• {self.current_display_name}: talk - Say hello
• {self.current_display_name}: help - Show this help
• {self.current_display_name}: ping - Test responsiveness
• {self.current_display_name}: room - Show room info
• {self.current_display_name}: db health - Check database
• {self.current_display_name}: db stats - Database statistics
• {self.current_display_name}: 8 [question] - Magic 8-ball fortune (uses NIST Beacon!)
• {self.current_display_name}: bible - Get a random Bible verse (uses NIST Beacon!)
• {self.current_display_name}: bible song - Get a Bible verse + related song (uses NIST Beacon!)
• {self.current_display_name}: advise <question> - Get serious, thoughtful advice (uses NIST Beacon!)
• {self.current_display_name}: advice <question> - Get funny, unconventional advice (uses NIST Beacon!)"""

                if AIOHTTP_AVAILABLE and os.getenv("OPENROUTER_API_KEY"):
                    help_text += f"\n• {self.current_display_name}: summary <youtube_url> - Summarize YouTube video"
                    help_text += f"\n• {self.current_display_name}: subs <youtube_url> - Extract closed captions from YouTube video"
                    help_text += f"\n• {self.current_display_name}: ask <question> - Ask about the most recent YouTube video"
                    help_text += f"\n• {self.current_display_name}: ask <youtube_url> <question> - Ask about a specific YouTube video"
                    help_text += f"\n• {self.current_display_name}: videos - List recently processed videos"

                await self.send_message(room.room_id, help_text)

            elif matches_exact("ping"):
                edit_note = " (responding to edit)" if is_edit else ""
                await self.send_message(room.room_id, f"{edit_prefix}{self.current_display_name.title()} Pong! 🏓 (from {event.sender}){edit_note}")

            elif matches_exact("room"):
                member_count = len(room.users)
                encrypted = "🔒 Encrypted" if room.encrypted else "🔓 Not encrypted"
                room_info = f"""{edit_prefix}🏠 **Room Debug Info:**
• Name: {room.name}
• Members: {member_count}
• Status: {encrypted}
• Room ID: {room.room_id}
• Bot events received: {sum(self.event_counters.values())}
• Bot name: {self.current_display_name}
• Media decryption: ✅ Enhanced
• Version: Simplified with dynamic naming"""

                await self.send_message(room.room_id, room_info)

            elif matches_exact("db health"):
                await self.handle_db_health_check(room.room_id, is_edit)

            elif matches_exact("db stats"):
                await self.handle_db_stats(room.room_id, is_edit)

            elif matches_command("8"):
                question = None
                command_start = f"{prefix} 8"
                if len(command) > len(command_start):
                    question = command[len(command_start):].strip()
                await self.handle_magic_8ball(room.room_id, question, is_edit)

            elif matches_exact("bible"):
                await self.handle_bible_verse(room.room_id, is_edit)

            elif matches_exact("bible song"):
                await self.handle_bible_song(room.room_id, is_edit)

            elif matches_command("advise") or matches_command("advice"):
                is_serious = matches_command("advise")
                command_start = f"{prefix} {'advise' if is_serious else 'advice'}"
                
                if len(command) > len(command_start):
                    advice_question = command[len(command_start):].strip()
                    if advice_question:
                        await self.handle_advice_request(room.room_id, advice_question, is_edit, is_serious)
                    else:
                        command_type = "advise" if is_serious else "advice"
                        error_msg = f"{edit_prefix}Please provide a question for advice. Usage: {self.current_display_name}: {command_type} <your question>"
                        await self.send_message(room.room_id, error_msg)
                else:
                    command_type = "advise" if is_serious else "advice"
                    error_msg = f"{edit_prefix}Please provide a question for advice. Usage: {self.current_display_name}: {command_type} <your question>"
                    await self.send_message(room.room_id, error_msg)

            elif matches_command("summary"):
                command_start = f"{prefix} summary"
                if len(command) > len(command_start):
                    url = command[len(command_start):].strip()
                    if url:
                        await self.handle_youtube_summary(room.room_id, url, is_edit)
                    else:
                        await self.send_message(room.room_id, f"{edit_prefix}Please provide a YouTube URL. Usage: {self.current_display_name}: summary <youtube_url>")
                else:
                    await self.send_message(room.room_id, f"{edit_prefix}Please provide a YouTube URL. Usage: {self.current_display_name}: summary <youtube_url>")

            elif matches_command("subs"):
                command_start = f"{prefix} subs"
                if len(command) > len(command_start):
                    url = command[len(command_start):].strip()
                    if url:
                        await self.handle_youtube_subs(room.room_id, url, is_edit)
                    else:
                        await self.send_message(room.room_id, f"{edit_prefix}Please provide a YouTube URL. Usage: {self.current_display_name}: subs <youtube_url>")
                else:
                    await self.send_message(room.room_id, f"{edit_prefix}Please provide a YouTube URL. Usage: {self.current_display_name}: subs <youtube_url>")

            elif matches_command("ask"):
                command_start = f"{prefix} ask"
                if len(command) > len(command_start):
                    question_part = command[len(command_start):].strip()
                    await self.handle_youtube_question(room.room_id, question_part, is_edit)
                else:
                    await self.send_message(room.room_id, f"{edit_prefix}Please provide a question. Usage: {self.current_display_name}: ask <question>")

            elif matches_exact("videos"):
                await self.handle_list_videos(room.room_id, is_edit)

            elif matches_exact("refresh name") or matches_exact("update name"):
                old_name = self.current_display_name
                success = await self.update_command_prefix()
                if success:
                    await self.send_message(room.room_id, f"{edit_prefix}🔄 **Name refresh completed!**\nOld name: `{old_name}`\nNew name: `{self.current_display_name}`")
                else:
                    await self.send_message(room.room_id, f"{edit_prefix}❌ **Name refresh failed!**\nCould not retrieve display name from Matrix.")

            else:
                unknown_msg = f"{edit_prefix}Unknown command. Try '{self.current_display_name}: help' or '{self.current_display_name}: debug'"
                await self.send_message(room.room_id, unknown_msg)

        except Exception as e:
            print(f"❌ Error handling bot command: {e}")
            import traceback
            traceback.print_exc()

    async def handle_youtube_question(self, room_id, question_part, is_edit=False):
        """Handle questions about YouTube videos"""
        if not AIOHTTP_AVAILABLE:
            await self.send_message(room_id, "❌ YouTube Q&A requires aiohttp. Install with: pip install aiohttp")
            return

        if not os.getenv("OPENROUTER_API_KEY"):
            await self.send_message(room_id, "❌ YouTube Q&A requires OPENROUTER_API_KEY in .env file")
            return

        try:
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
                    await self.send_message(room_id, f"{edit_prefix}❌ Please provide a question after the YouTube URL")
                    return
            else:
                # No URL provided, use most recent video for this room
                if room_id not in self.last_processed_video or not self.last_processed_video[room_id]:
                    await self.send_message(room_id, f"{edit_prefix}❌ No recent YouTube video found in this room. Please process a video first with '{self.current_display_name} summary <url>' or specify a URL in your question.")
                    return
                youtube_url = self.last_processed_video[room_id]

            # Get transcript from cache or extract it
            transcript_data = await self.get_or_extract_transcript(youtube_url, room_id, edit_prefix)
            
            if not transcript_data:
                return  # Error message already sent

            title, transcript = transcript_data

            await self.send_message(room_id, f"{edit_prefix}🤔 Analyzing video transcript to answer your question...")

            # Generate answer using AI
            answer = await self.answer_youtube_question(question, transcript, title)

            if answer:
                response = f"""{edit_prefix}💬 **Question about: {title}**

**Q:** {question}

**A:** {answer}"""
                await self.send_message(room_id, response)
            else:
                await self.send_message(room_id, f"{edit_prefix}❌ Failed to generate answer. Please try again later.")

        except Exception as e:
            print(f"Error in YouTube question handling: {e}")
            await self.send_message(room_id, f"{edit_prefix}❌ Error processing question: {str(e)}")

    async def handle_list_videos(self, room_id, is_edit=False):
        """List recently processed YouTube videos for this room"""
        edit_prefix = "✏️ " if is_edit else ""
        
        # Get cache for this room
        room_cache = self.transcript_cache.get(room_id, {})
        
        if not room_cache:
            await self.send_message(room_id, f"{edit_prefix}📹 No YouTube videos have been processed in this room yet.")
            return

        video_list = f"{edit_prefix}📹 **Recently Processed Videos (This Room):**\n\n"
        
        for i, (url, (title, _, timestamp)) in enumerate(room_cache.items(), 1):
            # Truncate title if too long
            display_title = title[:60] + "..." if len(title) > 60 else title
            recent_marker = " 🔄" if url == self.last_processed_video.get(room_id) else ""
            video_list += f"{i}. **{display_title}**{recent_marker}\n   `{url}`\n\n"

        video_list += f"💡 Use '{self.current_display_name} ask <question>' to ask about the most recent video{' 🔄' if self.last_processed_video.get(room_id) else ''}"
        
        await self.send_message(room_id, video_list)

    async def get_or_extract_transcript(self, youtube_url, room_id, edit_prefix) -> Optional[Tuple[str, str]]:
        """Get transcript from cache or extract it if not cached"""
        # Check cache for this room first
        room_cache = self.transcript_cache.get(room_id, {})
        
        if youtube_url in room_cache:
            print(f"📋 Using cached transcript for {youtube_url} in room {room_id}")
            title, transcript, _ = room_cache[youtube_url]
            return (title, transcript)

        # Not in cache, extract it
        await self.send_message(room_id, f"{edit_prefix}📥 Video not in cache, extracting transcript...")
        
        title = await self.get_youtube_title(youtube_url)
        transcript = await self.extract_youtube_subtitles(youtube_url)

        if not transcript:
            await self.send_message(room_id, f"{edit_prefix}❌ Could not extract transcript from video. The video might not have subtitles.")
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
                    f"{title} (Section {i+1}/{len(chunks)})",
                    is_chunk=True
                )
                
                if chunk_answer:
                    # Check if this chunk actually contains relevant information
                    # Simple heuristic: if the answer is too short or contains "doesn't contain", it's probably not relevant
                    if (len(chunk_answer.strip()) > 50 and
                        "doesn't contain" not in chunk_answer.lower() and
                        "no information" not in chunk_answer.lower() and
                        "not mentioned" not in chunk_answer.lower()):
                        chunk_answers.append(f"**Section {i+1}:** {chunk_answer}")
                        relevant_chunks += 1
                    else:
                        print(f"📝 Chunk {i+1} doesn't seem to contain relevant information")
                else:
                    print(f"⚠️ Failed to analyze chunk {i+1}")
            
            if not chunk_answers:
                return f"I searched through the entire transcript but couldn't find information that directly answers your question: '{question}'. The video might not cover this topic, or the information might be presented in a way that's difficult to extract from the transcript."
            
            print(f"✅ Found relevant information in {relevant_chunks} out of {len(chunks)} sections")
            
            # Step 3: Combine relevant chunk answers into final answer
            print(f"🔗 Combining information from {len(chunk_answers)} relevant sections...")
            
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

    async def get_nist_beacon_random_number(self):
        """Get current NIST Randomness Beacon value and return as integer"""
        try:
            if not AIOHTTP_AVAILABLE:
                print("Warning: aiohttp not available for NIST beacon, using fallback")
                import time
                return int(time.time())

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://beacon.nist.gov/beacon/2.0/pulse/last",
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
                        import time
                        return int(time.time())

        except Exception as e:
            print(f"Error getting NIST beacon value: {e}, using fallback")
            import time
            return int(time.time())

    async def get_nist_beacon_value(self):
        """Get current NIST Randomness Beacon value and determine positive/negative"""
        beacon_int = await self.get_nist_beacon_random_number()
        is_positive = (beacon_int % 2) == 0
        print(f"NIST Beacon determines: {'POSITIVE' if is_positive else 'NEGATIVE'}")
        return is_positive

    async def handle_magic_8ball(self, room_id, question=None, is_edit=False):
        """Generate a magic 8-ball style fortune using NIST Beacon + AI"""
        if not AIOHTTP_AVAILABLE:
            await self.send_message(room_id, "❌ Magic 8-ball requires aiohttp. Install with: pip install aiohttp")
            return

        if not os.getenv("OPENROUTER_API_KEY"):
            await self.send_message(room_id, "❌ Magic 8-ball requires OPENROUTER_API_KEY in .env file")
            return

        try:
            edit_prefix = "✏️ " if is_edit else ""
            if question:
                await self.send_message(room_id, f"{edit_prefix}🎱 *Consulting the NIST quantum oracle for: '{question}'...*")
            else:
                await self.send_message(room_id, f"{edit_prefix}🎱 *Consulting the NIST quantum oracle...*")

            is_positive = await self.get_nist_beacon_value()
            fortune = await self.generate_ai_fortune(question, is_positive)

            if fortune:
                beacon_info = "✨ *Determined by NIST Randomness Beacon quantum entropy*"
                if is_edit:
                    beacon_info += " (responding to edit)"
                await self.send_message(room_id, f"{edit_prefix}🎱 {fortune}\n\n{beacon_info}")
            else:
                await self.send_message(room_id, f"{edit_prefix}🎱 The quantum spirits are unclear... try again later.")

        except Exception as e:
            print(f"Error in magic 8-ball: {e}")
            await self.send_message(room_id, f"{edit_prefix}🎱 The magic 8-ball is broken! Try again later.")

    async def handle_bible_verse(self, room_id, is_edit=False):
        """Get a random Bible verse using NIST Beacon"""
        try:
            edit_prefix = "✏️ " if is_edit else ""
            await self.send_message(room_id, f"{edit_prefix}📖 *Consulting the NIST quantum scripture selector...*")

            bible_file = "kjv.txt"
            if not os.path.exists(bible_file):
                await self.send_message(room_id, f"{edit_prefix}❌ Bible file (kjv.txt) not found. Please download it from https://openbible.com/textfiles/kjv.txt")
                return

            verses = await self.parse_bible_file(bible_file)
            if not verses:
                await self.send_message(room_id, f"{edit_prefix}❌ Could not parse Bible file. Please check the format.")
                return

            beacon_number = await self.get_nist_beacon_random_number()
            verse_index = beacon_number % len(verses)
            selected_verse = verses[verse_index]

            print(f"Selected verse {verse_index + 1} of {len(verses)} using NIST beacon")

            beacon_info = "✨ *Verse selected by NIST Randomness Beacon quantum entropy*"
            if is_edit:
                beacon_info += " (responding to edit)"

            response = f"{edit_prefix}📖 **{selected_verse['reference']}**\n\n*{selected_verse['text']}*\n\n{beacon_info}"
            await self.send_message(room_id, response)

        except Exception as e:
            print(f"Error in Bible verse selection: {e}")
            await self.send_message(room_id, f"{edit_prefix}📖 The quantum scripture selector encountered an error. Perhaps this is a sign to reflect quietly.")

    async def handle_bible_song(self, room_id, is_edit=False):
        """Get a random Bible verse and find a thematically related song"""
        if not AIOHTTP_AVAILABLE:
            await self.send_message(room_id, "❌ Bible song feature requires aiohttp. Install with: pip install aiohttp")
            return

        if not os.getenv("OPENROUTER_API_KEY"):
            await self.send_message(room_id, "❌ Bible song feature requires OPENROUTER_API_KEY in .env file")
            return

        try:
            edit_prefix = "✏️ " if is_edit else ""
            await self.send_message(room_id, f"{edit_prefix}🎵 *Consulting the NIST quantum scripture & music archives...*")

            bible_file = "kjv.txt"
            if not os.path.exists(bible_file):
                await self.send_message(room_id, f"{edit_prefix}❌ Bible file (kjv.txt) not found. Please download it from https://openbible.com/textfiles/kjv.txt")
                return

            verses = await self.parse_bible_file(bible_file)
            if not verses:
                await self.send_message(room_id, f"{edit_prefix}❌ Could not parse Bible file. Please check the format.")
                return

            beacon_number = await self.get_nist_beacon_random_number()
            verse_index = beacon_number % len(verses)
            selected_verse = verses[verse_index]

            print(f"Selected verse {verse_index + 1} of {len(verses)} using NIST beacon for song pairing")

            song_recommendation = await self.find_thematic_song(selected_verse['text'])

            if song_recommendation:
                beacon_info = "✨ *Verse & song pairing selected by NIST Randomness Beacon quantum entropy*"
                if is_edit:
                    beacon_info += " (responding to edit)"

                response = f"""{edit_prefix}📖 **{selected_verse['reference']}**
*{selected_verse['text']}*

🎵 **Thematically Related Song:**
{song_recommendation}

{beacon_info}"""
                await self.send_message(room_id, response)
            else:
                response = f"""{edit_prefix}📖 **{selected_verse['reference']}**
*{selected_verse['text']}*

🎵 *Could not find a thematic song match - perhaps silence is the perfect accompaniment.*

✨ *Verse selected by NIST Randomness Beacon quantum entropy*"""
                await self.send_message(room_id, response)

        except Exception as e:
            print(f"Error in Bible song selection: {e}")
            await self.send_message(room_id, f"{edit_prefix}🎵 The quantum scripture & music selector encountered an error. Perhaps this calls for quiet contemplation.")

    async def handle_advice_request(self, room_id, question, is_edit=False, is_serious=True):
        """Generate advice using NIST Beacon + AI (serious or funny)"""
        if not AIOHTTP_AVAILABLE:
            await self.send_message(room_id, "❌ Advice feature requires aiohttp. Install with: pip install aiohttp")
            return

        if not os.getenv("OPENROUTER_API_KEY"):
            await self.send_message(room_id, "❌ Advice feature requires OPENROUTER_API_KEY in .env file")
            return

        try:
            edit_prefix = "✏️ " if is_edit else ""
            advice_type = "thoughtful wisdom" if is_serious else "unconventional wisdom"
            await self.send_message(room_id, f"{edit_prefix}🤔 *Consulting the NIST quantum {advice_type} archives...*")

            is_positive = await self.get_nist_beacon_value()

            if is_serious:
                advice = await self.generate_considerate_advice(question, is_positive)
                advice_label = "**Quantum-Guided Thoughtful Advice:**"
            else:
                advice = await self.generate_funny_advice(question, is_positive)
                advice_label = "**Quantum-Guided Unconventional Advice:**"

            if advice:
                beacon_info = "🌌 *Advice polarity determined by NIST quantum randomness*"
                if is_edit:
                    beacon_info += " (responding to edit)"
                await self.send_message(room_id, f"{edit_prefix}💡 {advice_label}\n{advice}\n\n{beacon_info}")
            else:
                fallback = "try consulting a wise friend instead!" if is_serious else "try asking a rubber duck instead!"
                await self.send_message(room_id, f"{edit_prefix}🤷 The quantum wisdom generators are offline... {fallback}")

        except Exception as e:
            print(f"Error generating advice: {e}")
            if is_serious:
                await self.send_message(room_id, f"{edit_prefix}💥 The thoughtful advice system encountered an error. Perhaps that's advice in itself - sometimes we need to pause and reflect.")
            else:
                await self.send_message(room_id, f"{edit_prefix}💥 The quantum advice machine exploded! This is probably good advice in itself.")

    async def parse_bible_file(self, file_path):
        """Parse the KJV Bible text file and return list of verses"""
        try:
            verses = []

            with open(file_path, 'r', encoding='utf-8') as file:
                for line in file:
                    line = line.strip()
                    if not line:
                        continue

                    if '\t' in line:
                        parts = line.split('\t', 1)
                        if len(parts) == 2:
                            reference = parts[0].strip()
                            text = parts[1].strip()

                            if reference and text:
                                verses.append({
                                    'reference': reference,
                                    'text': text
                                })

            print(f"Loaded {len(verses)} Bible verses from {file_path}")
            return verses

        except Exception as e:
            print(f"Error parsing Bible file: {e}")
            return []

    def create_Youtube_url(self, song_text):
        """Create a Youtube URL from song title and artist"""
        try:
            import urllib.parse

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

    async def find_thematic_song(self, bible_text):
        """Find a song that shares thematic elements with the Bible verse"""
        try:
            openrouter_key = os.getenv("OPENROUTER_API_KEY")
            if not openrouter_key: return None

            prompt = f"""Return only a song title and creator that shares thematic elements, imagery, or emotional resonance with the text: {bible_text}
Format your response EXACTLY as: "Song Title" by Artist Name
Do NOT include any YouTube links or URLs. Just the song title and artist."""

            payload = {"model": "cognitivecomputations/dolphin3.0-mistral-24b:free", "messages": [{"role": "user", "content": prompt}], "max_tokens": 100, "temperature": 0.8, "top_p": 0.9}
            headers = {"Authorization": f"Bearer {openrouter_key}", "Content-Type": "application/json", "HTTP-Referer": "https://github.com/matrix-nio/matrix-nio", "X-Title": "Matrix Bot"}

            async with aiohttp.ClientSession() as session:
                async with session.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status == 200:
                        data = await response.json()
                        song_rec = data['choices'][0]['message']['content'].strip().strip('"').strip("'").strip()
                        youtube_url = self.create_Youtube_url(song_rec)
                        return f"{song_rec}\nYoutube: {youtube_url}"
                    else:
                        print(f"OpenRouter API error {response.status}")
                        return None

        except Exception as e:
            print(f"Error finding thematic song: {e}")
            return None

    async def generate_ai_fortune(self, question=None, is_positive=True):
        """Generate a creative fortune using AI with NIST-determined polarity"""
        try:
            openrouter_key = os.getenv("OPENROUTER_API_KEY")
            if not openrouter_key: return None

            polarity = "POSITIVE/YES" if is_positive else "NEGATIVE/NO"

            if question:
                prompt = f"""You are a bold, decisive magic 8-ball oracle powered by NIST quantum randomness. Someone asks: "{question}"
The NIST Randomness Beacon has determined this answer should be {polarity}.
Give a CLEAR {polarity.lower()} answer with mystical flair:
{"POSITIVE/YES examples:" if is_positive else "NEGATIVE/NO examples:"}
{'''"The cosmic winds STRONGLY favor this venture - quantum forces align!"''' if is_positive else '''"The quantum realm SCREAMS warning - avoid this path!"'''}
Be mystical, dramatic, and CLEARLY {polarity.lower()}! Reference quantum/cosmic forces. 1-2 sentences max."""
            else:
                prompt = f"""You are a dramatic magic 8-ball oracle powered by NIST quantum randomness.
The quantum realm has determined this fortune should be {polarity}.
Give a {polarity.lower()} mystical fortune with cosmic flair:
{"POSITIVE examples:" if is_positive else "NEGATIVE examples:"}
{'''"Quantum entanglement brings tremendous fortune to your timeline!"''' if is_positive else '''"Dark quantum fluctuations gather around your path!"'''}
Reference quantum/cosmic forces and be CLEARLY {polarity.lower()}! 1-2 sentences max."""

            payload = {"model": "cognitivecomputations/dolphin3.0-mistral-24b:free", "messages": [{"role": "user", "content": prompt}], "max_tokens": 150, "temperature": 1.1, "top_p": 0.9}
            headers = {"Authorization": f"Bearer {openrouter_key}", "Content-Type": "application/json", "HTTP-Referer": "https://github.com/matrix-nio/matrix-nio", "X-Title": "Matrix Bot"}

            async with aiohttp.ClientSession() as session:
                async with session.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
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
            openrouter_key = os.getenv("OPENROUTER_API_KEY")
            if not openrouter_key: return None

            polarity_instruction = "ENCOURAGING and OPTIMISTIC" if is_positive else "CAUTIONARY and REALISTIC"

            prompt = f"""Someone asked for thoughtful advice: "{question}"
The NIST Randomness Beacon has determined this should be {polarity_instruction} advice.
Give SERIOUS, CONSIDERATE advice that's: {polarity_instruction} in tone, thoughtful and empathetic, practical and actionable, wise and mature, 2-3 sentences.
Be genuinely helpful, empathetic, and maintain the {polarity_instruction.lower()} tone."""

            payload = {"model": "cognitivecomputations/dolphin3.0-mistral-24b:free", "messages": [{"role": "user", "content": prompt}], "max_tokens": 200, "temperature": 0.7, "top_p": 0.9}
            headers = {"Authorization": f"Bearer {openrouter_key}", "Content-Type": "application/json", "HTTP-Referer": "https://github.com/matrix-nio/matrix-nio", "X-Title": "Matrix Bot"}

            async with aiohttp.ClientSession() as session:
                async with session.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
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
            openrouter_key = os.getenv("OPENROUTER_API_KEY")
            if not openrouter_key: return None

            polarity_instruction = "POSITIVE and ENCOURAGING" if is_positive else "CAUTIONARY and SKEPTICAL"

            prompt = f"""Someone asked for advice: "{question}"
The NIST Randomness Beacon has determined this should be {polarity_instruction} advice.
Give FUNNY, UNCONVENTIONAL advice that's: {polarity_instruction} in tone, hilariously absurd but somehow makes weird sense, creative and unexpected. 2-3 sentences max.
Be creative, weird, and funny while maintaining the {polarity_instruction.lower()} tone determined by quantum randomness!"""

            payload = {"model": "cognitivecomputations/dolphin3.0-mistral-24b:free", "messages": [{"role": "user", "content": prompt}], "max_tokens": 200, "temperature": 1.2, "top_p": 0.95}
            headers = {"Authorization": f"Bearer {openrouter_key}", "Content-Type": "application/json", "HTTP-Referer": "https://github.com/matrix-nio/matrix-nio", "X-Title": "Matrix Bot"}

            async with aiohttp.ClientSession() as session:
                async with session.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data['choices'][0]['message']['content'].strip().strip('"').strip("'").strip()
                    else:
                        print(f"OpenRouter API error {response.status}")
                        return None

        except Exception as e:
            print(f"Error generating funny advice: {e}")
            return None

    async def handle_db_health_check(self, room_id, is_edit=False):
        """Handle database health check command"""
        edit_prefix = "✏️ " if is_edit else ""

        if not self.db_enabled:
            await self.send_message(room_id, f"{edit_prefix}❌ Database is not enabled. Check your DATABASE_API_URL and DATABASE_API_KEY environment variables.")
            return

        try:
            await self.send_message(room_id, f"{edit_prefix}🏥 Checking database health...")

            is_healthy = await self.db_client.health_check()

            if is_healthy:
                await self.send_message(room_id, f"{edit_prefix}✅ **Database Health: HEALTHY**\n📊 API is responding normally")
            else:
                await self.send_message(room_id, f"{edit_prefix}❌ **Database Health: UNHEALTHY**\n🚨 API is not responding or having issues")

        except Exception as e:
            print(f"❌ Database health check error: {e}")
            await self.send_message(room_id, f"{edit_prefix}💥 **Database Health Check Failed**\n❌ Error: {str(e)}")

    async def handle_db_stats(self, room_id, is_edit=False):
        """Handle database statistics command"""
        edit_prefix = "✏️ " if is_edit else ""

        if not self.db_enabled:
            await self.send_message(room_id, f"{edit_prefix}❌ Database is not enabled.")
            return

        try:
            await self.send_message(room_id, f"{edit_prefix}📊 Fetching database statistics...")

            stats = await self.db_client.get_database_stats()

            if stats:
                stats_text = f"""{edit_prefix}📈 **Database Statistics**

📝 **Messages:** {stats.get('total_messages', 'Unknown')}
📁 **Media Files:** {stats.get('total_media_files', 'Unknown')}
💾 **Size:** {stats.get('total_size_mb', 0):.2f} MB
🕐 **Updated:** {stats.get('updated_at', 'Unknown')}

🔍 **Bot Counters:**
• Text: {self.event_counters['text_messages']}
• Media: {self.event_counters['media_messages']}
• Decrypt fails: {self.event_counters['decryption_failures']}
"""

                await self.send_message(room_id, stats_text)
            else:
                await self.send_message(room_id, f"{edit_prefix}❌ Failed to retrieve database statistics")

        except Exception as e:
            print(f"❌ Database stats error: {e}")
            await self.send_message(room_id, f"{edit_prefix}💥 **Database Stats Failed**\n❌ Error: {str(e)}")

    async def send_message(self, room_id, message):
        """Send a message to a room"""
        try:
            response = await self.client.room_send(
                room_id=room_id,
                message_type="m.room.message",
                content={
                    "msgtype": "m.text",
                    "body": message
                },
                ignore_unverified_devices=True
            )

            # Store our outgoing message in database
            if hasattr(response, 'event_id'):
                await self.store_message_in_db(
                    room_id=room_id,
                    event_id=response.event_id,
                    sender=self.user_id,
                    message_type="text",
                    content=message,
                    timestamp=datetime.now()
                )

            print(f"📤 Message sent: {message[:50]}{'...' if len(message) > 50 else ''}")
        except Exception as e:
            print(f"❌ Failed to send message: {e}")

    async def send_file_attachment(self, room_id, file_path, description="File"):
        """Send a file as an attachment to a room"""
        try:
            # Get file info first
            file_size = os.path.getsize(file_path)
            filename = os.path.basename(file_path)

            # Determine mimetype
            if file_path.endswith('.txt'):
                mimetype = "text/plain"
            else:
                mimetype = "application/octet-stream"

            # Read the file and create a BytesIO object
            with open(file_path, 'rb') as f:
                file_data = f.read()

            # Wrap bytes in BytesIO to create a file-like object
            file_like_obj = io.BytesIO(file_data)

            # Upload the file to Matrix
            response, maybe_keys = await self.client.upload(
                file_like_obj,  # Pass file-like object instead of raw bytes
                content_type=mimetype,
                filename=filename,
                filesize=file_size
            )

            if hasattr(response, 'content_uri'):
                # Send the file message
                content = {
                    "body": filename,
                    "info": {
                        "size": file_size,
                        "mimetype": mimetype,
                    },
                    "msgtype": "m.file",
                    "url": response.content_uri,
                }

                # Add encryption info if file was encrypted
                if maybe_keys:
                    content["file"] = {
                        "url": response.content_uri,
                        "key": maybe_keys["key"],
                        "iv": maybe_keys["iv"],
                        "hashes": maybe_keys["hashes"],
                        "v": maybe_keys["v"]
                    }

                send_response = await self.client.room_send(
                    room_id=room_id,
                    message_type="m.room.message",
                    content=content,
                    ignore_unverified_devices=True
                )

                # Store file message in database
                if hasattr(send_response, 'event_id'):
                    db_result = await self.store_message_in_db(
                        room_id=room_id,
                        event_id=send_response.event_id,
                        sender=self.user_id,
                        message_type="file",
                        content=f"File: {filename} ({file_size} bytes)",
                        timestamp=datetime.now()
                    )

                    # Upload the actual file to database if message was stored
                    if db_result and 'id' in db_result:
                        try:
                            await self.db_client.upload_media(db_result['id'], file_path)
                            print(f"📁 Uploaded file to database: {filename}")
                        except Exception as upload_error:
                            print(f"⚠️ Failed to upload file to database: {upload_error}")

                print(f"File attachment sent: {filename} ({file_size} bytes)")
                return True
            else:
                print(f"File upload failed: {response}")
                await self.send_message(room_id, f"❌ Failed to upload file: {filename}")
                return False

        except Exception as e:
            print(f"Error sending file attachment: {e}")
            import traceback
            traceback.print_exc()
            await self.send_message(room_id, f"❌ Error sending file attachment: {str(e)}")
            return False

    async def handle_youtube_summary(self, room_id, url, is_edit=False):
        """Handle YouTube video summarization"""
        if not AIOHTTP_AVAILABLE:
            await self.send_message(room_id, "❌ YouTube summary feature requires aiohttp. Install with: pip install aiohttp")
            return

        if not os.getenv("OPENROUTER_API_KEY"):
            await self.send_message(room_id, "❌ YouTube summary feature requires OPENROUTER_API_KEY in .env file")
            return

        try:
            edit_prefix = "✏️ " if is_edit else ""
            await self.send_message(room_id, f"{edit_prefix}🔄 Extracting subtitles from YouTube video...")

            # Extract subtitles using yt-dlp
            subtitles = await self.extract_youtube_subtitles(url)

            if not subtitles:
                await self.send_message(room_id, f"{edit_prefix}❌ No subtitles found for this video. The video might not have subtitles or be unavailable.")
                return

            await self.send_message(room_id, f"{edit_prefix}🤖 Generating summary using AI...")

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
                await self.send_message(room_id, response)
            else:
                await self.send_message(room_id, f"{edit_prefix}❌ Failed to generate summary. Please try again later.")

        except Exception as e:
            print(f"Error in YouTube summary: {e}")
            await self.send_message(room_id, f"{edit_prefix}❌ Error processing video: {str(e)}")

    async def handle_youtube_subs(self, room_id, url, is_edit=False):
        """Handle YouTube subtitle extraction command"""
        try:
            edit_prefix = "✏️ " if is_edit else ""

            await self.send_message(room_id, f"{edit_prefix}📹 *Extracting closed captions from YouTube video...*")

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
                await self.send_file_attachment(room_id, temp_file_path, f"Closed captions for: {title}")

                # Send confirmation message
                await self.send_message(room_id, f"{edit_prefix}✅ **Closed captions extracted and attached!**\n📄 File: `{os.path.basename(temp_file_path)}`\n💾 Size: {file_size:,} bytes\n🎬 Video: {title}")

                # Clean up local file after sending
                os.remove(temp_file_path)
                print(f"Cleaned up local file: {temp_file_path}")
            else:
                await self.send_message(room_id, f"{edit_prefix}❌ No closed captions found for this video.\n🎬 Video: {title}")

        except Exception as e:
            print(f"Error handling YouTube subs: {e}")
            await self.send_message(room_id, f"{edit_prefix}❌ Error processing YouTube URL: {str(e)}")

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

    async def login(self):
        """Login to Matrix server"""
        print("🔐 Attempting to login to Matrix server...")
        try:
            response = await self.client.login(self.password, device_name=self.device_name)

            if isinstance(response, LoginResponse):
                print(f"✅ Logged in as {self.user_id}")
                print(f"   Device ID: {response.device_id}")
                print(f"   Access Token: {response.access_token[:20]}...")

                # Update command prefix after successful login
                await self.update_command_prefix()
                if self.current_display_name:
                    print(f"🤖 Bot will respond to commands like: '{self.current_display_name}: help'")

                if self.client.olm:
                    self.client.olm.account.generate_one_time_keys(1)
                    print("✅ Encryption enabled and ready")
                    self.client.blacklist_device = lambda device: False
                    print("✅ Device verification disabled for bot operation")
                    await self.setup_encryption_keys()

                return True
            else:
                print(f"❌ Login failed: {response}")
                return False
        except Exception as e:
            print(f"❌ Login error: {e}")
            return False

    async def join_room(self, room_id):
        """Join a specific room"""
        print(f"🚪 Attempting to join room: {room_id}")
        try:
            response = await self.client.join(room_id)
            if hasattr(response, 'room_id'):
                print(f"✅ Joined room: {response.room_id}")
                return True
            else:
                print(f"❌ Failed to join room: {response}")
                return False
        except Exception as e:
            print(f"❌ Error joining room: {e}")
            return False

    async def setup_encryption_keys(self):
        """Set up encryption keys and trust devices"""
        try:
            await self.client.keys_upload()
            print("✅ Uploaded encryption keys")

            response = await self.client.keys_query()
            if isinstance(response, KeysQueryResponse):
                print("✅ Queried device keys for other users")

                for user_id, devices in response.device_keys.items():
                    for device_id, device_key in devices.items():
                        self.client.verify_device(device_key)
                        print(f"✅ Trusted device {device_id} for user {user_id}")

        except Exception as e:
            print(f"❌ Error setting up encryption keys: {e}")

    async def trust_all_room_devices(self, room_id):
        """Trust all devices in a specific room"""
        try:
            room = self.client.rooms.get(room_id)
            if not room:
                return

            user_ids = list(room.users.keys())
            if user_ids:
                response = await self.client.keys_query(user_ids)
                if isinstance(response, KeysQueryResponse):
                    for user_id, devices in response.device_keys.items():
                        for device_id, device_key in devices.items():
                            self.client.verify_device(device_key)
                            print(f"✅ Trusted device {device_id} for user {user_id}")

                    print(f"✅ Trusted all devices in room {room.name}")
        except Exception as e:
            print(f"❌ Error trusting room devices: {e}")

    async def sync_forever(self):
        """Keep syncing with the server"""
        print("🔄 Starting sync loop...")
        try:
            await self.client.sync_forever(timeout=30000)
        except Exception as e:
            print(f"❌ Sync error: {e}")
            raise

    async def close(self):
        """Close the client connection"""
        try:
            await self.client.close()
            print("✅ Client connection closed")
        except Exception as e:
            print(f"❌ Error closing client: {e}")

async def main():
    print("🔧 Starting SIMPLIFIED main function...")

    try:
        load_dotenv()
        print("✅ Environment variables loaded")
    except Exception as e:
        print(f"❌ Failed to load .env file: {e}")

    print(f"📁 Current working directory: {os.getcwd()}")
    print(f"📄 .env file exists: {os.path.exists('.env')}")

    # Configuration
    HOMESERVER = os.getenv("HOMESERVER", "https://matrix.org")
    USER_ID = os.getenv("USER_ID")
    PASSWORD = os.getenv("PASSWORD")
    ROOM_ID = os.getenv("ROOM_ID")

    print(f"\n📋 Configuration:")
    print(f"  HOMESERVER: {HOMESERVER}")
    print(f"  USER_ID: {USER_ID}")
    print(f"  PASSWORD: {'*' * len(PASSWORD) if PASSWORD else None}")
    print(f"  ROOM_ID: {ROOM_ID}")
    print(f"  DATABASE_API_URL: {os.getenv('DATABASE_API_URL', 'Not set')}")
    print(f"  DATABASE_API_KEY: {'*' * 10 if os.getenv('DATABASE_API_KEY') else 'Not set'}")
    print(f"  OPENROUTER_API_KEY: {'*' * 10 if os.getenv('OPENROUTER_API_KEY') else 'Not set'}")

    if not USER_ID or not PASSWORD or not ROOM_ID:
        print("❌ Error: Missing required environment variables")
        return

    print(f"\n🚀 Starting SIMPLIFIED bot for user: {USER_ID}")

    try:
        bot = DebugMatrixBot(HOMESERVER, USER_ID, PASSWORD)
        print("✅ Bot instance created successfully")
    except Exception as e:
        print(f"❌ Failed to create bot instance: {e}")
        return

    try:
        if await bot.login():
            print("✅ Login successful")

            if await bot.join_room(ROOM_ID):
                print("✅ Room joined successfully")

                # Trust devices in the room
                await bot.trust_all_room_devices(ROOM_ID)

                # Send startup message
                startup_msg = f"""🔍 **SIMPLIFIED Matrix Bot Started!**

🤖 **Available Commands:**
Type `boo help` for full command list

🔧 **Debug Info:**
• Database: {'✅ Enabled' if bot.db_enabled else '❌ Disabled'}
• Encryption: {'✅ Ready' if bot.client.olm else '❌ Disabled'}
• Media Processing: ✅ Enhanced decryption with MIME preservation
• YouTube Q&A: ✅ Room-specific transcript caching
• Version: Simplified with YouTube Q&A functionality

Ready to process encrypted media and provide quantum-enhanced responses! 🚀"""

                await bot.send_message(ROOM_ID, startup_msg)

                print(f"\n🎉 Simplified bot ready and running!")
                print(f"📊 Event counters will be displayed as messages are processed")
                print(f"🔓 Enhanced encrypted media decryption ready")
                print(f"📁 Database integration: {'✅ Active' if bot.db_enabled else '❌ Disabled'}")
                print(f"🎬 YouTube Q&A: ✅ Room-specific caching enabled")

                # Start the sync loop
                await bot.sync_forever()
            else:
                print("❌ Failed to join room")
        else:
            print("❌ Login failed")

    except KeyboardInterrupt:
        print("\n🛑 Received interrupt signal - shutting down gracefully...")
    except Exception as e:
        print(f"❌ Bot error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("🧹 Cleaning up...")
        await bot.close()
        print("✅ Cleanup complete")

if __name__ == "__main__":
    print("🎬 Starting SIMPLIFIED Matrix Bot with Enhanced Features...")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bot shutdown requested by user")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("🔚 Simplified Bot stopped")
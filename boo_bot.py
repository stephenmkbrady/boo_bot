#!/usr/bin/env python3
"""
Matrix Chatbot with Clean Plugin Architecture
"""

print("🚀 Starting Clean Matrix Bot with Plugin System...")

# Core imports only - NO plugin-specific imports
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
    exit(1)

try:
    from nio import (
        AsyncClient, MatrixRoom, RoomMessageText, RoomMessageMedia,
        RoomMessageImage, RoomMessageFile, RoomMessageAudio, RoomMessageVideo,
        LoginResponse, KeysUploadResponse, KeysQueryResponse, RoomMessage,
        Event
    )
    from nio.crypto import Olm, decrypt_attachment
    from nio.exceptions import OlmUnverifiedDeviceError
    from nio.events import MegolmEvent
    import base64

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
    exit(1)

# Import ONLY the plugin manager - not specific plugins
try:
    from plugins.plugin_manager import PluginManager
    print("✅ Plugin manager imported successfully")
    PLUGIN_SYSTEM_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Warning: Could not import plugin manager: {e}")
    PLUGIN_SYSTEM_AVAILABLE = False

# Optional imports for enhanced features
try:
    import aiohttp
    import aiofiles
    AIOHTTP_AVAILABLE = True
    print("✅ aiohttp and aiofiles imported successfully")
except ImportError:
    AIOHTTP_AVAILABLE = False
    print("⚠️ Warning: aiohttp/aiofiles not installed.")

try:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.backends import default_backend
    import base64
    import hashlib
    CRYPTO_AVAILABLE = True
    print("✅ cryptography library available")
except ImportError:
    CRYPTO_AVAILABLE = False
    print("⚠️ Warning: cryptography library not installed.")

# Load environment variables
load_dotenv('./.env')

class CleanMatrixBot:
    def __init__(self, homeserver, user_id, password, device_name="CleanMatrixBot"):
        print(f"🤖 Initializing Clean Matrix Bot...")
        print(f"   Homeserver: {homeserver}")
        print(f"   User ID: {user_id}")
        print(f"   Device: {device_name}")

        self.homeserver = homeserver
        self.user_id = user_id
        self.password = password
        self.device_name = device_name

        # Core bot properties
        self.store_path = "./bot_store"
        self.temp_media_dir = "./temp_media"
        
        # Ensure directories exist
        os.makedirs(self.store_path, exist_ok=True)
        os.makedirs(self.temp_media_dir, exist_ok=True)

        # Event counters
        self.event_counters = {
            'text_messages': 0,
            'media_messages': 0,
            'unknown_events': 0,
            'encrypted_events': 0,
            'decryption_failures': 0
        }

        # Bot name handling
        self.current_display_name = None
        self.last_name_check = None

        # Initialize Matrix client
        try:
            self.client = AsyncClient(homeserver, user_id, store_path=self.store_path)
            print("✅ AsyncClient initialized successfully")
        except Exception as e:
            print(f"❌ Failed to initialize AsyncClient: {e}")
            raise

        # Initialize plugin system - NO hard-coded plugins!
        self.plugin_manager = None
        if PLUGIN_SYSTEM_AVAILABLE:
            self.plugin_manager = PluginManager()
            print("✅ Plugin manager initialized")
        else:
            print("⚠️ Plugin system not available")
        
        # Database client for testing
        self.db_enabled = False
        self.db_client = None

        # Register event callbacks
        self._register_event_callbacks()

    def _register_event_callbacks(self):
        """Register Matrix event callbacks"""
        try:
            # Text messages
            self.client.add_event_callback(self.text_message_callback, RoomMessageText)

            # Media messages
            self.client.add_event_callback(self.media_message_callback, RoomMessageImage)
            self.client.add_event_callback(self.media_message_callback, RoomMessageFile)
            self.client.add_event_callback(self.media_message_callback, RoomMessageAudio)
            self.client.add_event_callback(self.media_message_callback, RoomMessageVideo)

            # Encrypted media messages
            if ENCRYPTED_EVENTS_AVAILABLE:
                self.client.add_event_callback(self.encrypted_media_callback, RoomEncryptedImage)
                self.client.add_event_callback(self.encrypted_media_callback, RoomEncryptedVideo)
                self.client.add_event_callback(self.encrypted_media_callback, RoomEncryptedAudio)
                self.client.add_event_callback(self.encrypted_media_callback, RoomEncryptedFile)

            # General callbacks
            self.client.add_event_callback(self.general_message_callback, RoomMessage)
            self.client.add_event_callback(self.decryption_failure_callback, MegolmEvent)
            
            # Room membership changes for key sharing
            from nio.events import RoomMemberEvent
            self.client.add_event_callback(self.room_member_callback, RoomMemberEvent)

            print("✅ Event callbacks registered successfully")
        except Exception as e:
            print(f"❌ Failed to register event callbacks: {e}")
            raise

    async def initialize_plugins(self):
        """Initialize plugin system after bot is set up"""
        if self.plugin_manager:
            print("🔌 Discovering and loading plugins...")
            results = await self.plugin_manager.discover_and_load_plugins(self)
            
            if results:
                loaded = sum(1 for success in results.values() if success)
                failed = len(results) - loaded
                print(f"✅ Plugin initialization complete: {loaded} loaded, {failed} failed")
                
                # Show available commands
                commands = self.plugin_manager.get_all_commands()
                if commands:
                    print(f"📋 Available commands: {', '.join(commands.keys())}")
            else:
                print("⚠️ No plugins found in plugins directory")

    async def get_bot_display_name(self):
        """Get the bot's current display name from Matrix"""
        try:
            print(f"🔍 Fetching display name for {self.user_id}")
            response = await self.client.get_displayname(self.user_id)
            
            if hasattr(response, 'displayname'):
                if response.displayname:
                    display_name = response.displayname.strip()
                    print(f"🤖 Bot display name retrieved: '{display_name}'")
                    return display_name
                else:
                    print(f"⚠️ Display name is empty for bot user {self.user_id}")
                    return None
            else:
                print(f"⚠️ Response has no displayname attribute")
                return None
        except Exception as e:
            print(f"❌ Error getting display name: {e}")
            return None

    async def update_command_prefix(self, retry_count=3):
        """Update the command prefix based on current display name"""
        for attempt in range(retry_count):
            try:
                display_name = await self.get_bot_display_name()
                if display_name:
                    self.current_display_name = display_name
                    print(f"✅ Bot display name updated to: '{self.current_display_name}'")
                    return True
                else:
                    if attempt < retry_count - 1:
                        print(f"⚠️ Could not retrieve display name (attempt {attempt + 1}/{retry_count}), retrying...")
                        await asyncio.sleep(1)  # Wait 1 second before retry
                        continue
                    else:
                        print(f"❌ Could not retrieve display name after {retry_count} attempts")
                        self.current_display_name = None
                        return False
            except Exception as e:
                if attempt < retry_count - 1:
                    print(f"❌ Error updating command prefix (attempt {attempt + 1}/{retry_count}): {e}, retrying...")
                    await asyncio.sleep(1)
                    continue
                else:
                    print(f"❌ Error updating command prefix after {retry_count} attempts: {e}")
                    self.current_display_name = None
                    return False
        return False

    async def text_message_callback(self, room: MatrixRoom, event: RoomMessageText):
        """Handle incoming text messages"""
        try:
            self.event_counters['text_messages'] += 1

            print(f"📨 TEXT MESSAGE #{self.event_counters['text_messages']}")
            print(f"📨   Room: {room.name}")
            print(f"📨   From: {event.sender}")
            print(f"📨   Content: {event.body}")

            # Ignore our own messages
            if event.sender == self.user_id:
                return

            # Update command prefix periodically
            current_time = datetime.now()
            if (self.last_name_check is None or
                (current_time - self.last_name_check).seconds > 300):  # Check every 5 minutes
                await self.update_command_prefix()
                self.last_name_check = current_time

            # Only process commands if we have a valid display name
            if not self.current_display_name:
                print(f"🚫 No display name set, attempting to retrieve it...")
                # Try to update display name once more
                success = await self.update_command_prefix(retry_count=1)
                if not success:
                    print(f"🚫 Still no display name available, ignoring message")
                    return

            # Store the message in database if enabled
            if self.db_enabled and self.db_client:
                try:
                    print(f"💾 Storing text message in database...")
                    result = await self.db_client.store_message(
                        room_id=room.room_id,
                        event_id=event.event_id,
                        sender=event.sender,
                        message_type="text",
                        content=event.body,
                        timestamp=datetime.fromtimestamp(event.server_timestamp / 1000) if event.server_timestamp else datetime.now()
                    )
                    
                    if result:
                        print(f"✅ Text message stored with ID: {result.get('id')}")
                    else:
                        print(f"❌ Failed to store text message")
                        
                except Exception as store_error:
                    print(f"❌ Error storing text message: {store_error}")

            # Handle bot commands
            await self.handle_command(room, event)

        except Exception as e:
            print(f"❌ Error in text message callback: {e}")

    async def handle_command(self, room: MatrixRoom, event: RoomMessageText):
        """Handle bot commands using plugin system"""
        try:
            message = event.body.strip()
            
            # Check if this is an edit
            is_edit = (hasattr(event, 'relates_to') and event.relates_to) or message.startswith("* ")
            edit_prefix = "✏️ " if is_edit else ""
            
            # Clean edit prefix if present
            if message.startswith("* "):
                message = message[2:].strip()
            
            # Check for bot command format: "botname: command args"
            expected_prefix = f"{self.current_display_name.lower()}:"
            message_lower = message.lower()
            
            if not message_lower.startswith(expected_prefix):
                return  # Not a command for this bot
            
            # Extract command and args
            command_part = message[len(expected_prefix):].strip()
            if not command_part:
                await self.send_message(room.room_id, f"{edit_prefix}Please specify a command. Try '{self.current_display_name}: help'")
                return
            
            # Split into command and arguments
            parts = command_part.split(" ", 1)
            command = parts[0].lower()
            args = parts[1] if len(parts) > 1 else ""
            
            print(f"🤖 Processing command: {command} with args: {args}")
            
            # Try to handle with plugin system
            if self.plugin_manager:
                response = await self.plugin_manager.handle_command(
                    command, args, room.room_id, event.sender, self
                )
                
                if response:
                    await self.send_message(room.room_id, f"{edit_prefix}{response}")
                    return
            
            # No plugin handled the command
            await self.send_message(room.room_id, f"{edit_prefix}Unknown command: {command}")

        except Exception as e:
            print(f"❌ Error handling command: {e}")

    async def media_message_callback(self, room: MatrixRoom, event):
        """Handle regular media messages"""
        try:
            self.event_counters['media_messages'] += 1
            
            if event.sender == self.user_id:
                return  # Ignore our own messages
            
            print(f"📎 MEDIA MESSAGE #{self.event_counters['media_messages']}")
            print(f"📎   Type: {type(event).__name__}")
            print(f"📎   From: {event.sender}")
            print(f"📎   Content: {getattr(event, 'body', 'No body')}")
            print(f"📎   Decrypted: {getattr(event, 'decrypted', False)}")
            
            # Debug room encryption status
            print(f"🔐 Room {room.room_id} encrypted: {room.encrypted}")
            if hasattr(room, 'encryption_algorithm'):
                print(f"🔐 Encryption algorithm: {room.encryption_algorithm}")
            
            # Store media message in database if enabled
            if self.db_enabled and self.db_client:
                await self._store_media_message(room, event)
            
        except Exception as e:
            print(f"❌ Error in media message callback: {e}")

    async def _store_media_message(self, room: MatrixRoom, event):
        """Store media message and handle both encrypted/unencrypted downloads"""
        try:
            # Determine message type based on event type
            event_type_name = type(event).__name__
            if 'Image' in event_type_name:
                message_type = 'image'
            elif 'Video' in event_type_name:
                message_type = 'video'
            elif 'Audio' in event_type_name:
                message_type = 'audio'
            elif 'File' in event_type_name:
                message_type = 'file'
            else:
                message_type = 'media'
            
            # Get message content/filename
            content = getattr(event, 'body', f"Media file: {getattr(event, 'url', 'unknown')}")
            
            print(f"💾 Storing {message_type} message in database...")
            
            # Store message record first
            result = await self.db_client.store_message(
                room_id=room.room_id,
                event_id=event.event_id,
                sender=event.sender,
                message_type=message_type,
                content=content,
                timestamp=datetime.now()
            )
            
            if result and 'id' in result:
                message_id = result['id']
                print(f"✅ Media message stored with ID: {message_id}")
                
                # Download and decrypt media
                await self._download_and_upload_media(event, message_id)
                
            else:
                print(f"❌ Failed to store media message in database")
                
        except Exception as e:
            print(f"❌ Error storing media message: {e}")

    async def _download_and_upload_media(self, event, message_id):
        """Download media (with decryption if needed) and upload to database"""
        try:
            if not hasattr(event, 'url') or not event.url:
                print(f"⚠️ No media URL found in event")
                return
                
            print(f"📥 Downloading media from Matrix: {event.url}")
            
            # Get media info
            filename = getattr(event, 'body', f"media_{event.event_id}")
            mimetype = getattr(event, 'mimetype', None)
            
            # Extract encryption info if this is encrypted media
            encryption_info = None
            if hasattr(event, 'key') and hasattr(event, 'iv') and hasattr(event, 'hashes'):
                encryption_info = {
                    'key': event.key,  # This is already a dict with the 'k' field
                    'iv': event.iv,
                    'hashes': event.hashes
                }
                print(f"🔐 Extracted encryption info from event attributes")
            elif hasattr(event, 'file') and event.file:
                # Encryption info might be in the 'file' field
                file_info = event.file
                if isinstance(file_info, dict):
                    encryption_info = {
                        'key': file_info.get('key', {}),
                        'iv': file_info.get('iv'),
                        'hashes': file_info.get('hashes', {})
                    }
                    print(f"🔐 Extracted encryption info from file field")
            
            # Download using the working method
            download_result = await self._download_matrix_media_working(
                event.url,
                filename,
                encryption_info,
                original_mimetype=mimetype
            )
            
            if download_result:
                if isinstance(download_result, tuple):
                    local_file_path, original_mimetype = download_result
                else:
                    local_file_path = download_result
                    original_mimetype = mimetype
                
                # Upload to database using existing method
                if self.db_client:
                    result = await self.db_client.upload_media(message_id, local_file_path)
                    if result:
                        print(f"📤 ✅ Uploaded media to database: {result}")
                        # Clean up temp file
                        try:
                            import os
                            os.unlink(local_file_path)
                            print(f"🗑️ Cleaned up temp file: {local_file_path}")
                        except:
                            pass
            else:
                print("❌ Failed to download media file")
                
        except Exception as e:
            print(f"❌ Error downloading/uploading media: {e}")

    async def _download_matrix_media_working(self, mxc_url, filename=None, encryption_info=None, original_mimetype=None):
        """Download and decrypt media from Matrix server using working method"""
        if not AIOHTTP_AVAILABLE:
            print("❌ Cannot download media - aiohttp not available")
            return None

        try:
            print(f"📥 Starting media download:")
            print(f"📥   MXC URL: {mxc_url}")
            print(f"📥   Filename: {filename}")
            print(f"📥   Original MIME Type: {original_mimetype}")
            print(f"📥   Has encryption info: {encryption_info is not None}")

            # Download the media using matrix-nio's download method
            print(f"📥 Calling client.download()...")
            response = await self.client.download(mxc_url)

            print(f"📥 Download response type: {type(response)}")
            if hasattr(response, 'body'):
                print(f"📥 ✅ Download successful - body size: {len(response.body)} bytes")

                # Check if we need to decrypt the content
                decrypted_data = response.body
                if encryption_info:
                    print(f"🔓 Attempting to decrypt media content...")
                    try:
                        # Use matrix-nio's decrypt_attachment
                        # Extract the actual base64 key string from the key dict
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

                        print(f"🔓 Decryption parameters available")
                        print(f"🔓   Expected hash: {expected_hash[:20]}...")

                        # Use matrix-nio's decrypt_attachment with corrected parameters
                        decrypted_data = decrypt_attachment(
                            ciphertext=response.body,
                            key=key_b64,  # Pass the base64 string, not the dict
                            hash=expected_hash,
                            iv=iv_b64
                        )
                        print(f"🔓 ✅ Successfully decrypted media using nio - size: {len(decrypted_data)} bytes")

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
                from pathlib import Path
                filepath = Path(self.temp_media_dir) / filename

                # Write file
                try:
                    import aiofiles
                    async with aiofiles.open(filepath, 'wb') as f:
                        await f.write(decrypted_data)
                except ImportError:
                    # Fallback if aiofiles not available
                    with open(filepath, 'wb') as f:
                        f.write(decrypted_data)

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

    def _is_encrypted_media_event(self, event):
        """Check if this is an encrypted media event using working detection"""
        # Check if this has encryption attributes (working approach)
        has_encryption_attrs = (
            hasattr(event, 'key') and 
            hasattr(event, 'iv') and 
            hasattr(event, 'hashes')
        )
        
        # Check if event has file encryption info
        has_file_encryption = (
            hasattr(event, 'file') and 
            event.file and 
            isinstance(event.file, dict) and
            'key' in event.file
        )
        
        # Check if it's decrypted (indicates it was originally encrypted)
        is_decrypted = getattr(event, 'decrypted', False)
        
        result = has_encryption_attrs or has_file_encryption or is_decrypted
        print(f"🔍 Encryption detection: attrs={has_encryption_attrs}, file={has_file_encryption}, decrypted={is_decrypted} -> {result}")
        
        return result

    async def _decrypt_media(self, event, encrypted_data):
        """Decrypt encrypted media using matrix-nio crypto functions"""
        try:
            print(f"🔐 DEBUG: Starting decryption for {type(event).__name__}")
            print(f"🔐 DEBUG: Event attributes: {dir(event)}")
            
            # Check different possible locations for encryption info
            print(f"🔐 DEBUG: Checking event.file...")
            if hasattr(event, 'file'):
                print(f"🔐 DEBUG: event.file = {event.file}")
                if event.file:
                    print(f"🔐 DEBUG: event.file attributes: {dir(event.file)}")
            
            print(f"🔐 DEBUG: Checking event.url...")
            if hasattr(event, 'url'):
                print(f"🔐 DEBUG: event.url = {event.url}")
            
            # Check for other encryption-related attributes
            for attr in ['encrypted_file', 'ciphertext', 'key', 'iv', 'hashes']:
                if hasattr(event, attr):
                    print(f"🔐 DEBUG: Found {attr} = {getattr(event, attr)}")
            
            if not hasattr(event, 'file') or not event.file:
                print(f"❌ No encryption info found in encrypted media event")
                print(f"🔐 DEBUG: Available event attributes: {[attr for attr in dir(event) if not attr.startswith('_')]}")
                return None
                
            # Extract decryption parameters
            key_data = event.file.key
            if not key_data or 'k' not in key_data:
                print(f"❌ No decryption key found in media event")
                return None
                
            key = key_data['k']  # Base64 encoded AES key
            iv = event.file.iv   # Base64 encoded initialization vector
            hashes = event.file.hashes  # SHA256 hash for verification
            
            
            # Decrypt using matrix-nio crypto function
            decrypted_data = decrypt_attachment(
                encrypted_data,
                key,
                iv, 
                hashes
            )
            
            print(f"✅ Media decrypted successfully ({len(decrypted_data)} bytes)")
            return decrypted_data
            
        except Exception as e:
            print(f"❌ Error decrypting media: {e}")
            import traceback
            print(f"🔐 DEBUG: Full traceback: {traceback.format_exc()}")
            return None

    async def _upload_media_to_database(self, media_data, event, message_id):
        """Upload media to database with validation"""
        try:
            # Validate media data
            if not media_data or len(media_data) == 0:
                print(f"❌ Empty media data, skipping upload")
                return
                
            # Check if data looks like valid file format
            if self._validate_media_format(media_data, event):
                print(f"✅ Media format validated")
            else:
                print(f"⚠️ Media format validation failed - may still be encrypted")
                
            # Create temporary file
            import tempfile
            import os
            
            filename = getattr(event, 'body', 'media_file')
            file_ext = os.path.splitext(filename)[1] if '.' in filename else ''
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
                temp_file.write(media_data)
                temp_file_path = temp_file.name
            
            print(f"📤 Uploading media to database...")
            
            # Upload to database
            upload_result = await self.db_client.upload_media(message_id, temp_file_path)
            
            # Clean up temp file
            os.unlink(temp_file_path)
            
            if upload_result:
                print(f"✅ Media uploaded successfully: {upload_result.get('filename', 'unknown')}")
            else:
                print(f"❌ Failed to upload media to database")
                
        except Exception as e:
            print(f"❌ Error uploading media: {e}")

    def _validate_media_format(self, data, event):
        """Basic validation to check if media was decrypted properly"""
        if not data or len(data) < 16:
            return False
            
        # Check for common file format headers
        headers = data[:16]
        
        # JPEG: FF D8 FF
        if headers.startswith(b'\xff\xd8\xff'):
            return True
        # PNG: 89 50 4E 47
        if headers.startswith(b'\x89PNG'):
            return True
        # GIF: 47 49 46 38
        if headers.startswith(b'GIF8'):
            return True
        # WebP: 52 49 46 46
        if headers.startswith(b'RIFF') and b'WEBP' in headers:
            return True
            
        # If no known format detected, it might still be encrypted
        print(f"⚠️ Unknown file format header: {headers.hex()}")
        return False

    async def encrypted_media_callback(self, room: MatrixRoom, event):
        """Handle encrypted media messages"""
        try:
            self.event_counters['encrypted_events'] += 1
            
            if event.sender == self.user_id:
                return
            
            print(f"📎🔐 ENCRYPTED MEDIA MESSAGE #{self.event_counters['encrypted_events']}")
            print(f"📎🔐   Type: {type(event).__name__}")
            print(f"📎🔐   From: {event.sender}")
            print(f"📎🔐   Content: {getattr(event, 'body', 'Encrypted media')}")
            
            # Store encrypted media message in database if enabled
            if self.db_enabled and self.db_client:
                await self._store_media_message(room, event)
            
        except Exception as e:
            print(f"❌ Error in encrypted media callback: {e}")

    async def general_message_callback(self, room: MatrixRoom, event: RoomMessage):
        """Catch-all for messages"""
        if event.sender == self.user_id:
            return
        
        # This is where you could add general message logging to database
        # if you had a database plugin loaded

    async def decryption_failure_callback(self, room: MatrixRoom, event: MegolmEvent):
        """Enhanced decryption failure handling with retry logic"""
        self.event_counters['decryption_failures'] += 1
        print(f"🔓 DECRYPTION FAILURE #{self.event_counters['decryption_failures']}")
        print(f"🔓   Room: {room.display_name} ({room.room_id})")
        print(f"🔓   Event type: {type(event).__name__}")
        print(f"🔓   Session ID: {event.session_id}")
        print(f"🔓   Sender: {event.sender}")
        print(f"🔓   Room encrypted: {room.encrypted}")
        
        # Check if this might be encrypted media
        if hasattr(event, 'ciphertext'):
            print(f"🔓   Ciphertext length: {len(event.ciphertext)}")
            
        # Check encryption keys state
        if hasattr(self.client, 'olm') and self.client.olm:
            if hasattr(self.client.olm, 'inbound_group_sessions'):
                session_count = len(self.client.olm.inbound_group_sessions)
                print(f"🔓   Available group sessions: {session_count}")
            
        try:
            # Try to request the room key
            await self.client.request_room_key(event)
            print(f"🔑 Requested room key for session {event.session_id}")
            
            # If too many failures, try to re-share keys
            if self.event_counters['decryption_failures'] % 10 == 0:
                print(f"🔄 Too many failures, resharing room keys...")
                await self.client.share_group_session(room.room_id)
                
        except Exception as e:
            print(f"❌ Failed to handle decryption failure: {e}")

    async def room_member_callback(self, room, event):
        """Handle room membership changes and share keys"""
        try:
            if event.membership == "join" and room.encrypted:
                # Share room keys with new member
                await self.client.share_group_session(room.room_id)
                print(f"🔑 Shared room keys for {room.room_id}")
        except Exception as e:
            print(f"❌ Error sharing room keys: {e}")

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
            print(f"📤 Message sent: {message[:50]}{'...' if len(message) > 50 else ''}")
            
            # Store message in database if enabled
            if self.db_enabled and self.db_client and hasattr(response, 'event_id'):
                await self.db_client.store_message(
                    room_id=room_id,
                    event_id=response.event_id,
                    sender=self.user_id,
                    message_type="text",
                    content=message,
                    timestamp=datetime.now()
                )
        except Exception as e:
            print(f"❌ Failed to send message: {e}")
    
    async def send_file(self, room_id, file_path, filename=None, mimetype=None):
        """Send a file to a room"""
        try:
            if not filename:
                filename = os.path.basename(file_path)
            
            if not mimetype:
                # Simple mimetype detection
                if filename.lower().endswith('.txt'):
                    mimetype = "text/plain"
                elif filename.lower().endswith('.json'):
                    mimetype = "application/json"
                else:
                    mimetype = "application/octet-stream"
            
            print(f"📎 Uploading file: {filename}")
            
            # Check if file exists
            if not os.path.exists(file_path):
                print(f"❌ File does not exist: {file_path}")
                return False
            
            # Read file and upload to Matrix
            with open(file_path, 'rb') as f:
                file_data = f.read()
                file_size = len(file_data)
            
            # Upload file to Matrix content repository
            upload_response = await self.client.upload(
                data_provider=lambda *args: file_data,
                content_type=mimetype,
                filename=filename,
                filesize=file_size
            )
            
            # Handle case where upload returns a tuple (response, error)
            if isinstance(upload_response, tuple):
                actual_response = upload_response[0]
                error = upload_response[1]
            else:
                actual_response = upload_response
                error = None
            
            if hasattr(actual_response, 'content_uri') and actual_response.content_uri and not error:
                # Send file message
                content = {
                    "msgtype": "m.file",
                    "body": filename,
                    "filename": filename,
                    "info": {
                        "size": file_size,
                        "mimetype": mimetype
                    },
                    "url": actual_response.content_uri
                }
                
                response = await self.client.room_send(
                    room_id=room_id,
                    message_type="m.room.message",
                    content=content,
                    ignore_unverified_devices=True
                )
                
                print(f"✅ File sent successfully: {filename}")
                return True
            else:
                print(f"❌ Failed to upload file: {actual_response}")
                if error:
                    print(f"❌ Upload error: {error}")
                if hasattr(actual_response, 'status_code'):
                    print(f"❌ Status code: {actual_response.status_code}")
                if hasattr(actual_response, 'message'):
                    print(f"❌ Error message: {actual_response.message}")
                return False
                
        except Exception as e:
            print(f"❌ Failed to send file: {e}")
            return False
    
    async def handle_bot_command(self, room, event, command_text):
        """Handle bot commands (deprecated, but kept for test compatibility)"""
        try:
            # Extract command from command_text
            if ":" in command_text:
                parts = command_text.split(":", 1)
                if len(parts) > 1:
                    command_part = parts[1].strip()
                    command_words = command_part.split()
                    if command_words:
                        command = command_words[0].lower()
                        
                        if command == "debug":
                            debug_info = f"""🔧 **DEBUG INFO**
Room: {room.name or 'Unknown'} ({room.room_id})
Encrypted: {room.encrypted}
Users: {len(room.users)}
Bot Display Name: {self.current_display_name}"""
                            await self.client.room_send(
                                room_id=room.room_id,
                                message_type="m.room.message",
                                content={"msgtype": "m.text", "body": debug_info},
                                ignore_unverified_devices=True
                            )
                        elif command == "talk":
                            await self.client.room_send(
                                room_id=room.room_id,
                                message_type="m.room.message",
                                content={"msgtype": "m.text", "body": "Hello! 👋 I'm your friendly Matrix bot. How can I help you today?"},
                                ignore_unverified_devices=True
                            )
                        else:
                            await self.client.room_send(
                                room_id=room.room_id,
                                message_type="m.room.message",
                                content={"msgtype": "m.text", "body": "Unknown command. Try 'boo: help' or 'boo: debug'"},
                                ignore_unverified_devices=True
                            )
        except Exception as e:
            print(f"❌ Error in handle_bot_command: {e}")
    
    async def store_message_in_db(self, room_id, event_id, sender, message_type, content):
        """Store a message in the database"""
        if not self.db_enabled or not self.db_client:
            return None
        
        try:
            return await self.db_client.store_message(
                room_id=room_id,
                event_id=event_id,
                sender=sender,
                message_type=message_type,
                content=content,
                timestamp=datetime.now()
            )
        except Exception as e:
            print(f"❌ Error storing message in DB: {e}")
            return None
    
    async def handle_db_health_check(self, room_id):
        """Handle database health check"""
        if not self.db_client:
            return
        
        try:
            is_healthy = await self.db_client.health_check()
            status = "HEALTHY" if is_healthy else "UNHEALTHY"
            message = f"🏥 Database Health: {status}"
            
            await self.client.room_send(
                room_id=room_id,
                message_type="m.room.message",
                content={"msgtype": "m.text", "body": message},
                ignore_unverified_devices=True
            )
        except Exception as e:
            print(f"❌ Error in handle_db_health_check: {e}")
    
    async def handle_db_stats(self, room_id):
        """Handle database statistics"""
        if not self.db_client:
            return
        
        try:
            stats = await self.db_client.get_database_stats()
            if stats:
                message = f"""📊 **Database Statistics**

📝 **Messages:** {stats.get('total_messages', 0)}
📁 **Media Files:** {stats.get('total_media_files', 0)}
💾 **Size:** {stats.get('total_size_mb', 0):.2f} MB
🕒 **Updated:** {stats.get('updated_at', 'Unknown')}"""
            else:
                message = "❌ Failed to retrieve database statistics"
            
            await self.client.room_send(
                room_id=room_id,
                message_type="m.room.message",
                content={"msgtype": "m.text", "body": message},
                ignore_unverified_devices=True
            )
        except Exception as e:
            print(f"❌ Error in handle_db_stats: {e}")

    # Standard Matrix bot methods (login, join_room, etc.)
    async def login(self):
        """Login to Matrix server"""
        print("🔐 Attempting to login to Matrix server...")
        try:
            response = await self.client.login(self.password, device_name=self.device_name)
            
            if isinstance(response, LoginResponse):
                print(f"✅ Logged in as {self.user_id}")
                
                # Update command prefix after login - with delay to allow sync
                print("⏳ Waiting 2 seconds for Matrix sync before getting display name...")
                await asyncio.sleep(2)
                await self.update_command_prefix()
                
                # Debug encryption setup
                await self._debug_encryption_setup()
                
                if self.client.olm:
                    print("✅ Encryption enabled and ready")
                    self.client.blacklist_device = lambda device: False
                    await self.setup_encryption_keys()
                else:
                    print("❌ Encryption not available - check matrix-nio[e2e] installation")
                
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
        """Enhanced encryption key setup with better error handling"""
        try:
            print("🔑 Setting up Matrix encryption keys...")
            
            # Upload our device keys
            await self.client.keys_upload()
            print("✅ Device keys uploaded")
            
            # Query and verify other users' keys
            response = await self.client.keys_query()
            if isinstance(response, KeysQueryResponse):
                verified_count = 0
                for user_id, devices in response.device_keys.items():
                    for device_id, device_key in devices.items():
                        # Trust all devices automatically (for bot use)
                        self.client.verify_device(device_key)
                        verified_count += 1
                print(f"✅ Verified {verified_count} device keys")
            else:
                print(f"⚠️ Key query response: {response}")
                
            # Request room keys for encrypted rooms
            await self._request_room_keys()
            
            print("✅ Encryption keys set up successfully")
            
        except Exception as e:
            print(f"❌ Error setting up encryption keys: {e}")

    async def _debug_encryption_setup(self):
        """Debug encryption configuration and state"""
        try:
            print(f"\n🔐 === ENCRYPTION DEBUG INFO ===")
            print(f"🔐 Bot device ID: {self.client.device_id}")
            print(f"🔐 Bot user ID: {self.client.user_id}")
            print(f"🔐 Store path: {self.client.store_path}")
            print(f"🔐 Trust own devices: {getattr(self.client, 'trust_own_devices', 'Not set')}")
            
            # Check if encryption is enabled
            if hasattr(self.client, 'olm') and self.client.olm:
                print(f"🔐 Olm object available: {type(self.client.olm)}")
                if hasattr(self.client.olm, 'account'):
                    print(f"🔐 Device keys: Available")
                else:
                    print(f"🔐 No olm.account available")
            else:
                print(f"🔐 Olm not available: {getattr(self.client, 'olm', 'None')}")
            
            # Check store directory
            import os
            if os.path.exists(self.store_path):
                store_files = os.listdir(self.store_path)
                print(f"🔐 Store directory contents: {store_files}")
            else:
                print(f"🔐 Store directory does not exist: {self.store_path}")
            
            print(f"🔐 === END ENCRYPTION DEBUG ===\n")
            
        except Exception as e:
            print(f"❌ Error in encryption debug: {e}")

    async def _request_room_keys(self):
        """Request encryption keys for all joined encrypted rooms"""
        try:
            for room_id, room in self.client.rooms.items():
                if room.encrypted:
                    print(f"🔐 Requesting keys for encrypted room: {room_id[:20]}...")
                    # Force key sharing request for this room
                    await self.client.share_group_session(room_id)
        except Exception as e:
            print(f"⚠️ Error requesting room keys: {e}")

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
            if self.plugin_manager:
                # Clean up plugins
                await self.plugin_manager.cleanup()
            
            await self.client.close()
            print("✅ Client connection closed")
        except Exception as e:
            print(f"❌ Error closing client: {e}")

# Clean main function
async def main():
    print("🔧 Starting clean Matrix bot...")

    # Load environment
    load_dotenv()

    # Configuration
    HOMESERVER = os.getenv("HOMESERVER", "https://matrix.org")
    USER_ID = os.getenv("USER_ID")
    PASSWORD = os.getenv("PASSWORD")
    ROOM_ID = os.getenv("ROOM_ID")

    if not USER_ID or not PASSWORD or not ROOM_ID:
        print("❌ Error: Missing required environment variables")
        return

    try:
        # Create bot
        bot = CleanMatrixBot(HOMESERVER, USER_ID, PASSWORD)
        print("✅ Bot instance created successfully")

        # Login
        if await bot.login():
            print("✅ Login successful")

            # Initialize plugins AFTER login
            await bot.initialize_plugins()

            # Join room
            if await bot.join_room(ROOM_ID):
                print("✅ Room joined successfully")

                # Send startup message
                plugin_info = ""
                if bot.plugin_manager:
                    status = bot.plugin_manager.get_plugin_status()
                    plugin_info = f"• Plugins: {status['total_loaded']} loaded, {status['total_failed']} failed"
                    if status.get('hot_reloading'):
                        plugin_info += " (🔥 Hot reloading active)"
                
                startup_msg = f"""🔍 **Clean Matrix Bot Started!**

🤖 **Available Commands:**
Type `{bot.current_display_name}: help` for commands

🔧 **Status:**
• Plugin System: {'✅ Active' if bot.plugin_manager else '❌ Disabled'}
{plugin_info}
• Encryption: {'✅ Ready' if bot.client.olm else '❌ Disabled'}

Ready and clean! 🚀"""

                await bot.send_message(ROOM_ID, startup_msg)
                print("🎉 Clean bot ready and running!")

                # Start sync loop
                await bot.sync_forever()
            else:
                print("❌ Failed to join room")
        else:
            print("❌ Login failed")

    except KeyboardInterrupt:
        print("\n🛑 Shutdown requested...")
    except Exception as e:
        print(f"❌ Bot error: {e}")
    finally:
        if 'bot' in locals():
            await bot.close()
        print("✅ Cleanup complete")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bot shutdown")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
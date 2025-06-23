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
            
            # Let plugins handle media if they want to
            # (This could be extended to call media-handling plugins)
            
        except Exception as e:
            print(f"❌ Error in media message callback: {e}")

    async def encrypted_media_callback(self, room: MatrixRoom, event):
        """Handle encrypted media messages"""
        try:
            self.event_counters['encrypted_events'] += 1
            
            if event.sender == self.user_id:
                return
            
            print(f"📎🔐 ENCRYPTED MEDIA MESSAGE #{self.event_counters['encrypted_events']}")
            print(f"📎🔐   Type: {type(event).__name__}")
            print(f"📎🔐   From: {event.sender}")
            
        except Exception as e:
            print(f"❌ Error in encrypted media callback: {e}")

    async def general_message_callback(self, room: MatrixRoom, event: RoomMessage):
        """Catch-all for messages"""
        if event.sender == self.user_id:
            return
        
        # This is where you could add general message logging to database
        # if you had a database plugin loaded

    async def decryption_failure_callback(self, room: MatrixRoom, event: MegolmEvent):
        """Handle decryption failures"""
        self.event_counters['decryption_failures'] += 1
        print(f"🔓 DECRYPTION FAILURE #{self.event_counters['decryption_failures']}")
        
        try:
            await self.client.request_room_key(event)
        except Exception as e:
            print(f"❌ Failed to request room key: {e}")

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
                    timestamp=datetime.now().isoformat()
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
                timestamp=datetime.now().isoformat()
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
                
                if self.client.olm:
                    print("✅ Encryption enabled and ready")
                    self.client.blacklist_device = lambda device: False
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
        """Set up encryption keys"""
        try:
            await self.client.keys_upload()
            response = await self.client.keys_query()
            if isinstance(response, KeysQueryResponse):
                for user_id, devices in response.device_keys.items():
                    for device_id, device_key in devices.items():
                        self.client.verify_device(device_key)
            print("✅ Encryption keys set up")
        except Exception as e:
            print(f"❌ Error setting up encryption keys: {e}")

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
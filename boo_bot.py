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

# Try to import youtube handler
try:
    from youtube_handler import youtube_handler, create_Youtube_url, YouTubeProcessor
    print("✅ youtube_handler imported successfully")
    YOUTUBE_HANDLER_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Warning: Could not import youtube_handler: {e}")
    print("YouTube audio download features will be disabled.")
    YOUTUBE_HANDLER_AVAILABLE = False

try:
    from ai_handler import AIProcessor
    print("✅ ai_handler imported successfully")
    AI_HANDLER_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Warning: Could not import ai_handler: {e}")
    print("AI features will be disabled.")
    AI_HANDLER_AVAILABLE = False

try:
    from media_handler import MediaProcessor
    print("✅ media_handler imported successfully")
    MEDIA_HANDLER_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Warning: Could not import media_handler: {e}")
    print("Media processing features will be disabled.")
    MEDIA_HANDLER_AVAILABLE = False

try:
    from config import BotConfig
    print("✅ config imported successfully")
    CONFIG_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Warning: Could not import config: {e}")
    print("Configuration management will be disabled.")
    CONFIG_AVAILABLE = False

try:
    from plugin_manager import PluginManager
    from youtube_plugin import YouTubePlugin
    from ai_plugin import AIPlugin
    from core_plugin import CorePlugin
    from database_plugin import DatabasePlugin
    print("✅ plugin system imported successfully")
    PLUGIN_SYSTEM_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Warning: Could not import plugin system: {e}")
    print("Plugin system will be disabled.")
    PLUGIN_SYSTEM_AVAILABLE = False

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

        # Initialize configuration system
        if CONFIG_AVAILABLE:
            self.config = BotConfig()
            print(f"✅ Configuration system initialized")
        else:
            self.config = None
            print(f"⚠️ Configuration system disabled")

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

        # Initialize handlers based on configuration
        self.youtube_processor = None
        self.ai_processor = None
        self.media_processor = None
        
        if self.config and self.config.is_feature_enabled("youtube") and YOUTUBE_HANDLER_AVAILABLE:
            self.youtube_processor = YouTubeProcessor()
            print("✅ YouTube handler enabled via configuration")
        elif YOUTUBE_HANDLER_AVAILABLE and not self.config:
            # Fallback to old behavior if config not available
            self.youtube_processor = YouTubeProcessor()
            print("✅ YouTube handler enabled (fallback mode)")
        else:
            print("⚠️ YouTube handler disabled")

        if self.config and self.config.is_feature_enabled("ai") and AI_HANDLER_AVAILABLE:
            self.ai_processor = AIProcessor()
            print("✅ AI handler enabled via configuration")
        elif AI_HANDLER_AVAILABLE and not self.config:
            # Fallback to old behavior if config not available
            self.ai_processor = AIProcessor()
            print("✅ AI handler enabled (fallback mode)")
        else:
            print("⚠️ AI handler disabled")

        if self.config and self.config.is_feature_enabled("media") and MEDIA_HANDLER_AVAILABLE:
            media_config = self.config.get_feature_config("media")
            temp_dir = media_config.get("temp_dir", self.temp_media_dir)
            self.media_processor = MediaProcessor(temp_media_dir=temp_dir)
            print("✅ Media handler enabled via configuration")
        elif MEDIA_HANDLER_AVAILABLE and not self.config:
            # Fallback to old behavior if config not available
            self.media_processor = MediaProcessor(temp_media_dir=self.temp_media_dir)
            print("✅ Media handler enabled (fallback mode)")
        else:
            print("⚠️ Media handler disabled")

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

        # Initialize plugin system (after database init)
        self.plugin_manager = None
        if PLUGIN_SYSTEM_AVAILABLE:
            self._setup_plugins()
        else:
            print("⚠️ Plugin system disabled")

        # Add event callbacks for ALL message types + debugging
        try:
            # Text messages
            self.client.add_event_callback(self.text_message_callback, RoomMessageText)

            # Regular (unencrypted) media messages - delegate to media processor
            if self.media_processor:
                self.client.add_event_callback(self.media_message_callback_wrapper, RoomMessageImage)
                self.client.add_event_callback(self.media_message_callback_wrapper, RoomMessageFile)
                self.client.add_event_callback(self.media_message_callback_wrapper, RoomMessageAudio)
                self.client.add_event_callback(self.media_message_callback_wrapper, RoomMessageVideo)

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

    def _setup_plugins(self):
        """Set up plugins based on configuration"""
        try:
            self.plugin_manager = PluginManager()
            
            # Add core plugin (always enabled)
            core_plugin = CorePlugin(bot_instance=self)
            self.plugin_manager.add_plugin(core_plugin)
            print("✅ Core plugin added")
            
            # Add YouTube plugin if enabled
            if self.youtube_processor:
                youtube_plugin = YouTubePlugin()
                self.plugin_manager.add_plugin(youtube_plugin)
                print("✅ YouTube plugin added")
            
            # Add AI plugin if enabled
            if self.ai_processor:
                ai_plugin = AIPlugin()
                self.plugin_manager.add_plugin(ai_plugin)
                print("✅ AI plugin added")
            
            # Add database plugin if enabled
            if self.db_enabled:
                database_plugin = DatabasePlugin(bot_instance=self)
                self.plugin_manager.add_plugin(database_plugin)
                print("✅ Database plugin added")
                
            print(f"✅ Plugin system initialized with {len(self.plugin_manager.plugins)} plugins")
            
        except Exception as e:
            print(f"❌ Error setting up plugins: {e}")
            self.plugin_manager = None

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

    async def media_message_callback_wrapper(self, room: MatrixRoom, event):
        """Wrapper for regular media messages to delegate to media processor"""
        try:
            self.event_counters['media_messages'] += 1

            # Ignore our own messages
            if event.sender == self.user_id:
                print(f"📎 Ignoring our own media message")
                return

            # Use media processor if available
            if self.media_processor:
                await self.media_processor.handle_media_message(
                    room, event,
                    store_message_func=self.store_message_in_db,
                    db_client=self.db_client if self.db_enabled else None,
                    client=self.client
                )
            else:
                print(f"⚠️ Media processor not available, skipping media processing")

        except Exception as e:
            print(f"❌ Error in media message callback wrapper: {e}")
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

            # Use media processor if available
            if self.media_processor:
                await self.media_processor.handle_encrypted_media_message(
                    room, event, 
                    store_message_func=self.store_message_in_db,
                    db_client=self.db_client if self.db_enabled else None,
                    client=self.client
                )
            else:
                print(f"⚠️ Media processor not available, skipping encrypted media processing")


        except Exception as e:
            print(f"❌ Error in encrypted media message callback: {e}")
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

            # Try plugin system first
            command_handled = False
            if self.plugin_manager:
                # Extract command and args from the command text
                # Use lowercase version for command detection, but preserve original case for arguments
                if command_lower.startswith(prefix):
                    # Remove prefix from original command to preserve case in arguments
                    remaining_command = command[len(prefix):].strip()
                    command_parts = remaining_command.split(" ", 1)
                    if command_parts:
                        base_command = command_parts[0].lower()  # Command itself should be lowercase for matching
                        args = command_parts[1] if len(command_parts) > 1 else ""  # Args preserve original case
                    
                        # Try to handle with plugin system
                        response = await self.plugin_manager.handle_command(
                            base_command, args, room.room_id, event.sender
                        )
                        
                        if response:
                            await self.send_message(room.room_id, f"{edit_prefix}{response}")
                            command_handled = True
                        else:
                            pass

            # Fallback for unknown commands
            if not command_handled:
                unknown_msg = f"{edit_prefix}Unknown command. Try '{self.current_display_name}: help' or '{self.current_display_name}: debug'"
                await self.send_message(room.room_id, unknown_msg)

        except Exception as e:
            print(f"❌ Error handling bot command: {e}")
            import traceback
            traceback.print_exc()










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
                startup_msg = f"""🔍 **Matrix Bot Started!**

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
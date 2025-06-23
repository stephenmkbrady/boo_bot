# Clean Plugin System Separation

## Problem: Hard-Coded Plugin Dependencies

Your current `boo_bot.py` has several issues that break clean separation:

1. **Direct plugin imports** in the main bot file
2. **Hard-coded plugin initialization** 
3. **Plugin-specific knowledge** in core bot logic
4. **Mixed responsibilities** - bot handles both core Matrix logic AND plugin management

Let's fix this step by step.

## Step 1: Create Clean Plugin Interface

First, let's establish a proper plugin interface that the main bot can use without knowing about specific plugins.

```python
# plugin_interface.py (new file)
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any

class BotPlugin(ABC):
    """Base interface that all plugins must implement"""
    
    def __init__(self, name: str):
        self.name = name
        self.enabled = True
        self.version = "1.0.0"
        self.description = "A bot plugin"
        
    @abstractmethod
    def get_commands(self) -> List[str]:
        """Return list of commands this plugin handles"""
        pass
    
    @abstractmethod
    async def handle_command(self, command: str, args: str, room_id: str, user_id: str, bot_instance) -> Optional[str]:
        """Handle a command and return response or None"""
        pass
    
    async def initialize(self, bot_instance) -> bool:
        """Initialize plugin with bot instance. Return True if successful."""
        return True
    
    async def cleanup(self):
        """Cleanup when plugin is disabled/unloaded"""
        pass
    
    def can_handle(self, command: str) -> bool:
        """Check if this plugin can handle the command"""
        return command in self.get_commands()
    
    def get_info(self) -> Dict[str, Any]:
        """Return plugin information"""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "enabled": self.enabled,
            "commands": self.get_commands()
        }
```

## Step 2: Clean Plugin Manager

Create a plugin manager that discovers plugins automatically without the main bot needing to know about them.

```python
# plugin_manager.py (new file)
import os
import importlib
import importlib.util
from pathlib import Path
from typing import Dict, List, Optional
from plugin_interface import BotPlugin

class PluginManager:
    def __init__(self, plugins_dir: str = "plugins"):
        self.plugins: Dict[str, BotPlugin] = {}
        self.plugins_dir = Path(plugins_dir)
        self.failed_plugins: Dict[str, str] = {}
        
        # Ensure plugins directory exists
        self.plugins_dir.mkdir(exist_ok=True)
        
    async def discover_and_load_plugins(self, bot_instance) -> Dict[str, bool]:
        """Automatically discover and load all plugins from plugins directory"""
        results = {}
        
        # Look for all Python files in plugins directory
        for plugin_file in self.plugins_dir.glob("*_plugin.py"):
            plugin_name = plugin_file.stem
            success = await self.load_plugin_from_file(plugin_file, bot_instance)
            results[plugin_name] = success
            
        print(f"✅ Plugin discovery complete: {len(self.plugins)} loaded, {len(self.failed_plugins)} failed")
        return results
    
    async def load_plugin_from_file(self, plugin_file: Path, bot_instance) -> bool:
        """Load a specific plugin from file"""
        plugin_name = plugin_file.stem
        
        try:
            # Dynamically import the plugin module
            spec = importlib.util.spec_from_file_location(plugin_name, plugin_file)
            if not spec or not spec.loader:
                raise ImportError(f"Could not load spec for {plugin_file}")
                
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Find plugin class - look for classes that inherit from BotPlugin
            plugin_class = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and 
                    issubclass(attr, BotPlugin) and 
                    attr != BotPlugin):
                    plugin_class = attr
                    break
            
            if not plugin_class:
                raise ImportError(f"No BotPlugin subclass found in {plugin_file}")
            
            # Create plugin instance
            plugin = plugin_class()
            
            # Initialize plugin
            if await plugin.initialize(bot_instance):
                self.plugins[plugin.name] = plugin
                self.failed_plugins.pop(plugin_name, None)  # Clear any previous failures
                print(f"✅ Loaded plugin: {plugin.name} v{plugin.version}")
                return True
            else:
                raise Exception("Plugin initialization failed")
                
        except Exception as e:
            error_msg = f"Failed to load plugin {plugin_name}: {e}"
            print(f"❌ {error_msg}")
            self.failed_plugins[plugin_name] = str(e)
            return False
    
    async def handle_command(self, command: str, args: str, room_id: str, user_id: str, bot_instance) -> Optional[str]:
        """Try to handle command with available plugins"""
        for plugin in self.plugins.values():
            if plugin.enabled and plugin.can_handle(command):
                try:
                    result = await plugin.handle_command(command, args, room_id, user_id, bot_instance)
                    if result is not None:
                        return result
                except Exception as e:
                    print(f"❌ Plugin {plugin.name} error handling {command}: {e}")
                    # Continue to next plugin instead of crashing
                    continue
        return None
    
    def get_all_commands(self) -> Dict[str, str]:
        """Get all available commands mapped to plugin names"""
        commands = {}
        for plugin in self.plugins.values():
            if plugin.enabled:
                for cmd in plugin.get_commands():
                    commands[cmd] = plugin.name
        return commands
    
    def get_plugin_status(self) -> Dict[str, Any]:
        """Get status of all plugins"""
        return {
            "loaded": {name: plugin.get_info() for name, plugin in self.plugins.items()},
            "failed": self.failed_plugins,
            "total_loaded": len(self.plugins),
            "total_failed": len(self.failed_plugins)
        }
    
    def enable_plugin(self, plugin_name: str) -> bool:
        """Enable a specific plugin"""
        if plugin_name in self.plugins:
            self.plugins[plugin_name].enabled = True
            return True
        return False
    
    def disable_plugin(self, plugin_name: str) -> bool:
        """Disable a specific plugin"""
        if plugin_name in self.plugins:
            self.plugins[plugin_name].enabled = False
            return True
        return False
```

## Step 3: Remove Plugin Dependencies from Main Bot

Now let's clean up the main bot file to remove all plugin-specific imports and knowledge.

```python
# boo_bot_clean.py (updated main bot file)
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
    from plugin_manager import PluginManager
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
                self.current_display_name = display_name
                print(f"✅ Bot display name updated to: '{self.current_display_name}'")
                return True
            else:
                print(f"❌ Could not retrieve display name")
                self.current_display_name = None
                return False
        except Exception as e:
            print(f"❌ Error updating command prefix: {e}")
            self.current_display_name = None
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
                print(f"🚫 Ignoring message - no valid display name set")
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
            await self.client.room_send(
                room_id=room_id,
                message_type="m.room.message",
                content={
                    "msgtype": "m.text",
                    "body": message
                },
                ignore_unverified_devices=True
            )
            print(f"📤 Message sent: {message[:50]}{'...' if len(message) > 50 else ''}")
        except Exception as e:
            print(f"❌ Failed to send message: {e}")

    # Standard Matrix bot methods (login, join_room, etc.)
    async def login(self):
        """Login to Matrix server"""
        print("🔐 Attempting to login to Matrix server...")
        try:
            response = await self.client.login(self.password, device_name=self.device_name)
            
            if isinstance(response, LoginResponse):
                print(f"✅ Logged in as {self.user_id}")
                
                # Update command prefix after login
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
                for plugin in self.plugin_manager.plugins.values():
                    await plugin.cleanup()
            
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
```

## Step 4: Example Clean Plugin

Here's how plugins should look now - completely independent from the main bot:

```python
# plugins/core_plugin.py
from plugin_interface import BotPlugin
from typing import List, Optional

class CorePlugin(BotPlugin):
    def __init__(self):
        super().__init__("core")
        self.version = "1.0.0"
        self.description = "Core bot commands (help, debug, ping)"
        
    def get_commands(self) -> List[str]:
        return ["help", "debug", "ping", "status", "plugins"]
    
    async def handle_command(self, command: str, args: str, room_id: str, user_id: str, bot_instance) -> Optional[str]:
        if command == "help":
            return await self._handle_help(bot_instance)
        elif command == "debug":
            return await self._handle_debug(bot_instance)
        elif command == "ping":
            return "Pong! 🏓"
        elif command == "status":
            return await self._handle_status(bot_instance)
        elif command == "plugins":
            return await self._handle_plugins(bot_instance)
        
        return None
    
    async def _handle_help(self, bot_instance) -> str:
        if not bot_instance.plugin_manager:
            return "❌ Plugin system not available"
        
        commands = bot_instance.plugin_manager.get_all_commands()
        help_text = f"🤖 **{bot_instance.current_display_name} Commands:**\n\n"
        
        # Group commands by plugin
        by_plugin = {}
        for cmd, plugin_name in commands.items():
            if plugin_name not in by_plugin:
                by_plugin[plugin_name] = []
            by_plugin[plugin_name].append(cmd)
        
        for plugin_name, cmds in by_plugin.items():
            help_text += f"**{plugin_name.title()}:** {', '.join(cmds)}\n"
        
        return help_text
    
    async def _handle_debug(self, bot_instance) -> str:
        return f"""🔍 **DEBUG INFO**

📊 **Event Counters:**
• Text: {bot_instance.event_counters['text_messages']}
• Media: {bot_instance.event_counters['media_messages']}
• Encrypted: {bot_instance.event_counters['encrypted_events']}
• Decrypt fails: {bot_instance.event_counters['decryption_failures']}

🤖 **Bot Info:**
• Display name: {bot_instance.current_display_name}
• User ID: {bot_instance.user_id}
• Store path: {bot_instance.store_path}"""
    
    async def _handle_status(self, bot_instance) -> str:
        if not bot_instance.plugin_manager:
            return "❌ Plugin system not available"
        
        status = bot_instance.plugin_manager.get_plugin_status()
        return f"""📊 **Bot Status**

🔌 **Plugins:** {status['total_loaded']} loaded, {status['total_failed']} failed
📨 **Messages processed:** {bot_instance.event_counters['text_messages']}
🔐 **Encryption:** {'✅ Active' if bot_instance.client.olm else '❌ Disabled'}"""
    
    async def _handle_plugins(self, bot_instance) -> str:
        if not bot_instance.plugin_manager:
            return "❌ Plugin system not available"
        
        status = bot_instance.plugin_manager.get_plugin_status()
        response = "🔌 **Plugin Status:**\n\n"
        
        for name, info in status['loaded'].items():
            enabled_emoji = "✅" if info['enabled'] else "❌"
            response += f"{enabled_emoji} **{info['name']}** v{info['version']}\n"
            response += f"   {info['description']}\n"
            response += f"   Commands: {', '.join(info['commands'])}\n\n"
        
        if status['failed']:
            response += "❌ **Failed Plugins:**\n"
            for name, error in status['failed'].items():
                response += f"• {name}: {error}\n"
        
        return response
```

## Benefits of This Clean Separation

✅ **Zero Hard-coded Dependencies**: Main bot knows nothing about specific plugins  
✅ **True Plugin Discovery**: Plugins are loaded automatically from the plugins directory  
✅ **Clean Interfaces**: Plugin contract is well-defined and enforced  
✅ **Easy Testing**: Each component can be tested independently  
✅ **Simple Extension**: Add new plugins by just dropping files in the plugins directory  

## Migration Path

1. **Replace your current boo_bot.py** with the clean version above
2. **Create the plugin_interface.py** and **plugin_manager.py** files
3. **Move your existing features** into proper plugin files in the plugins directory
4. **Test that everything works** without hard-coded references

This gives you a truly modular system where the core bot is completely separated from plugin functionality!
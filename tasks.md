# Incremental Bot Refactoring: Step-by-Step Modernization

## Overview

This guide shows how to gradually modernize your Matrix chatbot without breaking anything. We'll start with minimal changes and progressively improve the architecture over time, keeping your bot running throughout the process.


## Step 1: Basic Configuration Management

**Goal**: Make features easily configurable without changing the core structure.

```python
# config.py (new file)
import os
from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class FeatureConfig:
    enabled: bool
    config: Dict[str, Any]

class BotConfig:
    def __init__(self):
        # Matrix config
        self.homeserver = os.getenv("HOMESERVER", "https://matrix.org")
        self.user_id = os.getenv("USER_ID")
        self.password = os.getenv("PASSWORD")
        self.room_id = os.getenv("ROOM_ID")
        
        # Feature flags
        self.features = {
            "youtube": FeatureConfig(
                enabled=bool(os.getenv("OPENROUTER_API_KEY")),
                config={"max_cached_per_room": 5}
            ),
            "ai": FeatureConfig(
                enabled=bool(os.getenv("OPENROUTER_API_KEY")),
                config={"model": "meta-llama/llama-3.2-3b-instruct:free"}
            ),
            "media": FeatureConfig(
                enabled=bool(os.getenv("DATABASE_API_KEY")),
                config={"temp_dir": "./temp_media"}
            ),
            "database": FeatureConfig(
                enabled=bool(os.getenv("DATABASE_API_KEY")),
                config={}
            )
        }
        
        # API keys
        self.openrouter_key = os.getenv("OPENROUTER_API_KEY")
        self.database_api_key = os.getenv("DATABASE_API_KEY")
        self.database_api_url = os.getenv("DATABASE_API_URL")
    
    def is_feature_enabled(self, feature_name: str) -> bool:
        return self.features.get(feature_name, FeatureConfig(False, {})).enabled
    
    def get_feature_config(self, feature_name: str) -> Dict[str, Any]:
        return self.features.get(feature_name, FeatureConfig(False, {})).config

# Update your main bot class:
class DebugMatrixBot:
    def __init__(self, homeserver, user_id, password, device_name="SimplifiedChatBot"):
        self.config = BotConfig()  # Add this line
        
        # ... existing init code ...
        
        # Initialize handlers based on config
        self.youtube_handler = None
        self.ai_handler = None
        self.media_handler = None
        
        if self.config.is_feature_enabled("youtube"):
            self.youtube_handler = YouTubeHandler(self.config.openrouter_key)
            
        if self.config.is_feature_enabled("ai"):
            self.ai_handler = AIHandler(self.config.openrouter_key)
            
        if self.config.is_feature_enabled("media"):
            self.media_handler = MediaHandler(self.db_client)
```

## Step 2: Simple Plugin Interface

**Goal**: Create a basic plugin system without changing existing code structure.

```python
# plugin_base.py (new file)
from abc import ABC, abstractmethod
from typing import List, Optional

class BotPlugin(ABC):
    def __init__(self, name: str):
        self.name = name
        self.enabled = True
    
    @abstractmethod
    def get_commands(self) -> List[str]:
        """Return commands this plugin handles"""
        pass
    
    @abstractmethod
    async def handle_command(self, command: str, args: str, room_id: str, user_id: str) -> Optional[str]:
        """Handle a command, return response or None"""
        pass
    
    def can_handle(self, command: str) -> bool:
        """Check if this plugin can handle the command"""
        return command in self.get_commands()

# Convert your handlers to plugins:
# youtube_plugin.py
from plugin_base import BotPlugin
from youtube_handler import YouTubeHandler

class YouTubePlugin(BotPlugin):
    def __init__(self, openrouter_key: str):
        super().__init__("youtube")
        self.handler = YouTubeHandler(openrouter_key)
    
    def get_commands(self) -> List[str]:
        return ["summary", "subs", "ask", "videos"]
    
    async def handle_command(self, command: str, args: str, room_id: str, user_id: str) -> Optional[str]:
        if command == "summary":
            return await self.handler.handle_summary_command(room_id, args)
        elif command == "ask":
            return await self.handler.handle_question_command(room_id, args)
        # ... handle other commands
        return None

# Simple plugin manager:
class PluginManager:
    def __init__(self):
        self.plugins: List[BotPlugin] = []
    
    def add_plugin(self, plugin: BotPlugin):
        self.plugins.append(plugin)
    
    def remove_plugin(self, plugin_name: str):
        self.plugins = [p for p in self.plugins if p.name != plugin_name]
    
    async def handle_command(self, command: str, args: str, room_id: str, user_id: str) -> Optional[str]:
        for plugin in self.plugins:
            if plugin.enabled and plugin.can_handle(command):
                return await plugin.handle_command(command, args, room_id, user_id)
        return None
    
    def get_all_commands(self) -> Dict[str, str]:
        commands = {}
        for plugin in self.plugins:
            if plugin.enabled:
                for cmd in plugin.get_commands():
                    commands[cmd] = plugin.name
        return commands
```

## Step 3: Gradual Command System Improvement

**Goal**: Improve command handling without breaking existing functionality.

```python
# In your main bot class, gradually replace command handling:
class DebugMatrixBot:
    def __init__(self, homeserver, user_id, password, device_name="SimplifiedChatBot"):
        # ... existing init ...
        
        # Add plugin manager
        self.plugin_manager = PluginManager()
        self._setup_plugins()
    
    def _setup_plugins(self):
        """Set up plugins based on configuration"""
        if self.config.is_feature_enabled("youtube"):
            youtube_plugin = YouTubePlugin(self.config.openrouter_key)
            self.plugin_manager.add_plugin(youtube_plugin)
            
        if self.config.is_feature_enabled("ai"):
            ai_plugin = AIPlugin(self.config.openrouter_key)
            self.plugin_manager.add_plugin(ai_plugin)
        
        # Always add core plugin
        core_plugin = CorePlugin()
        self.plugin_manager.add_plugin(core_plugin)
    
    async def handle_bot_command(self, room: MatrixRoom, event, command_text=None):
        # ... existing command parsing ...
        
        # Extract command and args
        command_parts = command.split(' ', 2)
        base_command = command_parts[1] if len(command_parts) > 1 else ""
        args = command_parts[2] if len(command_parts) > 2 else ""
        
        # Try plugin system first
        response = await self.plugin_manager.handle_command(
            base_command, args, room.room_id, event.sender
        )
        
        if response:
            await self.send_message(room.room_id, f"{edit_prefix}{response}")
            return
        
        # Fall back to existing command handling for now
        if matches_exact("debug"):
            # ... existing debug code ...
        # ... other existing commands ...
```

## Step 4: Environment-Based Configuration

**Goal**: Make configuration more flexible and environment-aware.

```python
# enhanced_config.py
import os
import yaml
from pathlib import Path
from typing import Dict, Any

class EnhancedBotConfig:
    def __init__(self, env_file: str = ".env"):
        self.env_file = env_file
        self.load_env_file()
        
        # Load plugin configuration
        self.plugin_config = self._load_plugin_config()
        
    def load_env_file(self):
        """Load environment variables from file"""
        if Path(self.env_file).exists():
            with open(self.env_file) as f:
                for line in f:
                    if '=' in line and not line.strip().startswith('#'):
                        key, value = line.strip().split('=', 1)
                        os.environ[key] = value
    
    def _load_plugin_config(self) -> Dict[str, Any]:
        """Load plugin configuration from YAML"""
        config_file = Path("config/plugins.yaml")
        if config_file.exists():
            with open(config_file) as f:
                return yaml.safe_load(f) or {}
        return {}
    
    def is_plugin_enabled(self, plugin_name: str) -> bool:
        """Check if plugin is enabled in config"""
        plugin_config = self.plugin_config.get(plugin_name, {})
        return plugin_config.get("enabled", False)
    
    def get_plugin_config(self, plugin_name: str) -> Dict[str, Any]:
        """Get configuration for specific plugin"""
        return self.plugin_config.get(plugin_name, {}).get("config", {})

# config/plugins.yaml (new file)
youtube:
  enabled: true
  config:
    max_cached_per_room: 5
    chunk_size: 8000

ai:
  enabled: true
  config:
    model: "meta-llama/llama-3.2-3b-instruct:free"
    temperature: 0.3
    max_tokens: 500

media:
  enabled: true
  config:
    temp_dir: "./temp_media"
    max_file_size: 50MB

database:
  enabled: true
  config:
    timeout: 30
```

## Step 5: Better Error Handling and Logging

**Goal**: Add better observability without changing core logic.

```python
# utils/logging_setup.py
import logging
import sys
from pathlib import Path

def setup_logging(level: str = "INFO", log_file: str = "bot.log"):
    """Set up structured logging"""
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Create logs directory
    Path("logs").mkdir(exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=log_format,
        handlers=[
            logging.FileHandler(f"logs/{log_file}"),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Set up logger for matrix-nio
    logging.getLogger("nio").setLevel(logging.WARNING)

# Add to your plugins:
class YouTubePlugin(BotPlugin):
    def __init__(self, openrouter_key: str):
        super().__init__("youtube")
        self.handler = YouTubeHandler(openrouter_key)
        self.logger = logging.getLogger(f"plugin.{self.name}")
    
    async def handle_command(self, command: str, args: str, room_id: str, user_id: str) -> Optional[str]:
        self.logger.info(f"Handling {command} command from {user_id} in {room_id}")
        
        try:
            if command == "summary":
                return await self.handler.handle_summary_command(room_id, args)
            # ... other commands
        except Exception as e:
            self.logger.error(f"Error handling {command}: {e}")
            return f"❌ Error processing {command} command"
        
        return None
```

## Migration Path Summary

```python

# Start:
boo_bot.py           # Core Matrix handling
youtube_handler.py   # YouTube features
ai_handler.py        # AI features  
media_handler.py     # Media features

# End state:
boo_bot.py           # Core Matrix + plugin manager
plugins/
  youtube_plugin/
    youtube_plugin.py  # Pluggable YouTube
  ai_plugin/
    ai_plugin.py       # Pluggable AI
  core_plugin/
    core_plugin.py     # Basic commands
config/
  plugins.yaml       # Feature configuration
```

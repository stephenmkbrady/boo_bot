# Boo Bot

![Space Hamster](test_data/test.jpg)

<div align="center">
<i>"Space hamsters are never wrong! - Minsc"</i>
</div>

Matrix chatbot with modular plugin architecture for AI features, YouTube processing, database integration, and more!

## 🚀 Quick Start

```bash
cd boo_bot/
docker-compose up --build -d
docker-compose logs boo_bot  # Check logs
docker-compose down         # CRITICAL - always clean up
```

## ✨ Features

- **Plugin Architecture**: Hot-reloadable modular system
- **YouTube Integration**: Summaries, subtitles, Q&A about videos
- **AI Features**: 8-ball, advice, Bible verses (NIST quantum randomness)
- **PIN Authentication**: 6-digit PINs for secure room access (works with minsc_saga frontend)
- **Database Integration**: Message and media storage via boo_memories API
- **File Uploads**: Send files directly to Matrix rooms

## 🎯 Available Commands

### Core Commands
- `help` - Show available commands
- `ping`, `status` - Bot health checks
- `plugins` - List loaded plugins
- `reload <plugin>` - Hot-reload specific plugin

### YouTube Plugin
- `youtube summary <URL>` - AI-powered video summary
- `youtube subs <URL>` - Extract subtitles as downloadable file
- `youtube <question>` - Ask questions about processed videos

### AI Plugin
- `8ball <question>` - Magic 8-ball with quantum randomness
- `advice <question>` - AI-generated advice
- `bible` - Random Bible verse
- `song <name>` - Create YouTube search URL
- `nist` - Get NIST Randomness Beacon value

### PIN Authentication Plugin
- `pin` or `getpin` - Request 6-digit PIN for current room
- PINs expire after 24 hours
- Rate limited: 3 requests per hour per room
- Used by minsc_saga frontend for secure dashboard access

### Database Plugin
- `db health` - Check database connectivity
- `db stats` - View database statistics

## ⚙️ Configuration

Create `.env` file in `boo_bot/`:

```bash
# Matrix Configuration
MATRIX_HOMESERVER_URL="https://your-matrix-server.com"
MATRIX_ACCESS_TOKEN="syt_your_matrix_access_token"

# Database Configuration (for boo_memories API)
DATABASE_URL="postgresql+asyncpg://user:password@host:port/database_name"
DATABASE_API_BASE_URL="https://your-api-server.com"
DATABASE_API_KEY="your_secure_api_key"

# AI Configuration
OPENROUTER_API_KEY="your_openrouter_api_key"

# Plugin Configuration
DEBUG_MODE=true
PLUGIN_HOT_RELOAD=true
```

## 🧩 Plugin Development

### Create Custom Plugin

1. **Create directory**: `mkdir plugins/myplugin && touch plugins/myplugin/{__init__.py,plugin.py}`

2. **Implement plugin** (`plugins/myplugin/plugin.py`):
```python
from plugins.plugin_interface import BotPlugin

class MyPlugin(BotPlugin):
    def __init__(self):
        super().__init__("myplugin")
        self.version = "1.0.0"
        self.description = "My custom plugin"
    
    def get_commands(self):
        return ["mycommand"]
    
    async def handle_command(self, command, args, room_id, user_id, bot_instance):
        if command == "mycommand":
            return f"Hello {user_id}! Args: {args}"
        return None
```

3. **Enable in config** (`config/plugins.yaml`):
```yaml
myplugin:
  enabled: true
  config:
    timeout: 30
```

### Plugin Features
- 🔥 **Hot Reloading**: Changes take effect immediately
- 🔍 **Auto Discovery**: Drop folders in `plugins/` directory
- ⚡ **Async Support**: Full async/await support
- 🛡️ **Error Isolation**: Plugin errors don't crash bot
- 📊 **Runtime Management**: Enable/disable without restart

## 🧪 Testing

```bash
# Run all tests
docker-compose exec boo_bot python -m pytest tests/ -v

# Run with coverage
docker-compose exec boo_bot python -m pytest tests/ --cov=boo_bot --cov=plugins --cov-report=html -v

# Run specific test suites
docker-compose exec boo_bot python -m pytest tests/test_api_client.py -v
docker-compose exec boo_bot python -m pytest tests/test_automated_file_cycle.py -v

# Run storage integration tests
docker-compose exec boo_bot python -m pytest tests/test_storage_simple.py -v
```

### Test Data

The test suite includes sample media files for testing file upload/download cycles:

- **`test_data/test.jpg`** - Sample JPEG image (1.4MB) used for:
  - File integrity testing (SHA256 hash verification)
  - Upload/download cycle validation
  - Media storage API integration tests
  - Encrypted media decryption testing

**Current Coverage**: 84 tests passing, 5 skipped (complex async mocking)

## 🏗️ Architecture

```
boo_bot/
├── boo_bot.py              # Main bot application
├── plugins/
│   ├── plugin_interface.py # Base plugin interface
│   ├── plugin_manager.py   # Plugin discovery & hot reload
│   ├── core/plugin.py      # Essential bot commands
│   ├── ai/plugin.py        # AI features with NIST randomness
│   ├── auth/plugin.py      # PIN authentication (NEW)
│   ├── database/plugin.py  # Database operations
│   ├── youtube/plugin.py   # YouTube processing
│   └── example/plugin.py   # Template (disabled)
├── config/
│   └── plugins.yaml        # Plugin configuration
└── tests/                  # Test suites
```

## 🔗 Integration

Works with:
- **boo_memories**: Backend API for message/media storage
- **minsc_saga**: React frontend dashboard (uses PIN authentication)

## 📚 Technologies

- [matrix-nio](https://github.com/matrix-nio/matrix-nio) - Matrix client library
- [OpenRouter.ai](https://openrouter.ai/) - AI model integration
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - YouTube processing
- [NIST Randomness Beacon](https://beacon.nist.gov/) - Quantum randomness
- Docker & asyncio for deployment and performance
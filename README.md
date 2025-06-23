# Boo Bot

This repository contains the `boo_bot` project, a proof-of-concept Matrix chatbot designed to interact with a Matrix homeserver. It uses the `matrix-nio` library for Matrix communication and an external API client (`api_client.py`) for database interactions.

**Note:** This project is currently a development proof of concept and is not production-ready.

## Features

*   **Matrix Homeserver Integration:** Communicates with a Matrix homeserver to send and receive messages.
*   **Clean Plugin Architecture:** Modular plugin system with hot reloading and automatic discovery.
*   **File Upload Support:** Upload files (like YouTube subtitles) directly to Matrix rooms.
*   **YouTube Integration:** Extract subtitles, generate summaries, and answer questions about videos.
*   **AI-Powered Features:** Magic 8-ball, advice generation, and Bible verse selection using NIST quantum randomness.
*   **Database Interaction:** Connects to an external database API for message and media storage.
*   **Asynchronous Operations:** Built with `asyncio` for efficient handling of I/O-bound tasks.

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

*   Python 3.9+
*   `pip` (Python package installer)

### Installation

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/stephenmkbrady/boo_bot.git
    cd boo_bot
    ```

2.  **Create a virtual environment (recommended):**

    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3.  **Install dependencies:**

    ```bash
    # For Arch based systems:
    pip install legacy-cgi
    CMAKE_POLICY_VERSION_MINIMUM=3.5 pip install matrix-nio[e2e]
    
    # For every system:
    pip install -r requirements.txt
    ```

### Configuration

Create a `.env` file in the `boo_bot/` directory with your environment variables. An example might include:

```
DATABASE_URL="postgresql+asyncpg://user:password@host:port/database_name"
MATRIX_HOMESERVER_URL="https://matrix.example.com"
MATRIX_ACCESS_TOKEN="syt_your_matrix_access_token"
```

### Running the Application


```bash
python boo_bot.py
```

The bot will connect to your Matrix homeserver and join the specified room.

## Plugin System

This bot features a modular plugin architecture that allows you to easily extend functionality without modifying the core bot code.

### Available Plugins

The bot comes with several built-in plugins:

#### Core Plugin (`plugins/core/`)
- **Commands:** `help`, `debug`, `ping`, `status`, `plugins`, `talk`, `room`, `refresh`, `update`, `name`, `reload`, `enable`, `disable`
- **Description:** Essential bot commands for status, debugging, and plugin management

#### YouTube Plugin (`plugins/youtube/`)
- **Commands:** `youtube`, `yt`
- **Description:** YouTube video processing, subtitles extraction, and AI summaries
- **Usage:**
  - `bot: youtube summary <URL>` - Get AI-powered video summary
  - `bot: youtube subs <URL>` - Extract subtitles as downloadable text file
  - `bot: youtube <question>` - Ask questions about processed videos

#### AI Plugin (`plugins/ai/`)
- **Commands:** `8ball`, `advice`, `advise`, `bible`, `song`, `nist`
- **Description:** AI-powered features using NIST quantum randomness
- **Usage:**
  - `bot: 8ball <question>` - Magic 8-ball with quantum randomness
  - `bot: advice <question>` - Get AI-generated advice
  - `bot: bible` - Random Bible verse selection
  - `bot: song <song name>` - Create YouTube search URL
  - `bot: nist` - Get current NIST Randomness Beacon value

#### Database Plugin (`plugins/database/`)
- **Commands:** `db`
- **Description:** Database health checks and statistics
- **Usage:**
  - `bot: db health` - Check database connectivity
  - `bot: db stats` - View database statistics

#### Example Plugin (`plugins/example/`)
- **Commands:** `echo`, `repeat`, `example`
- **Description:** Skeleton plugin for developers (disabled by default)
- **Status:** 🔴 Disabled (for reference only)

### Creating Custom Plugins

You can easily create custom plugins by following this structure:

#### 1. Create Plugin Directory Structure
```bash
mkdir plugins/myplugin
touch plugins/myplugin/__init__.py
touch plugins/myplugin/plugin.py
```

#### 2. Implement Plugin Class
Create `plugins/myplugin/plugin.py`:

```python
from typing import List, Optional
import logging
from plugins.plugin_interface import BotPlugin

class MyCustomPlugin(BotPlugin):
    def __init__(self):
        super().__init__("myplugin")
        self.version = "1.0.0"
        self.description = "My custom plugin description"
        self.logger = logging.getLogger(f"plugin.{self.name}")
    
    async def initialize(self, bot_instance) -> bool:
        """Initialize plugin with bot instance"""
        self.bot = bot_instance
        self.logger.info("My custom plugin initialized")
        return True
    
    def get_commands(self) -> List[str]:
        """Return list of commands this plugin handles"""
        return ["mycommand", "another"]
    
    async def handle_command(self, command: str, args: str, room_id: str, user_id: str, bot_instance) -> Optional[str]:
        """Handle commands for this plugin"""
        if command == "mycommand":
            return f"Hello {user_id}! You said: {args}"
        elif command == "another":
            return "This is another command!"
        return None
    
    async def cleanup(self):
        """Cleanup when plugin is unloaded"""
        self.logger.info("My custom plugin cleanup completed")
```

#### 3. Plugin Development Guidelines

**Required Methods:**
- `__init__()` - Initialize plugin with name, version, description
- `get_commands()` - Return list of command strings
- `handle_command()` - Process commands and return responses
- `initialize()` - Setup plugin with bot instance (optional)
- `cleanup()` - Clean up resources when unloaded (optional)

**Best Practices:**
- ✅ Use descriptive plugin and command names
- ✅ Add comprehensive error handling
- ✅ Include usage instructions in command responses
- ✅ Use logging for debugging: `self.logger.info/error/debug()`
- ✅ Return `None` if command not handled
- ✅ Return string responses for successful commands
- ✅ Handle empty/missing arguments gracefully

**Plugin Features:**
- 🔥 **Hot Reloading:** Plugins reload automatically when files change
- 🔍 **Auto Discovery:** Just drop plugin folders in `plugins/` directory
- ⚡ **Async Support:** Full async/await support for I/O operations
- 🛡️ **Error Isolation:** Plugin errors don't crash the bot
- 📊 **Runtime Management:** Enable/disable plugins without restart

#### 4. Using the Example Plugin

The bot includes a skeleton example plugin at `plugins/example/`. To use it as a template:

1. **Copy the example plugin:**
   ```bash
   cp -r plugins/example plugins/mynewplugin
   ```

2. **Edit the plugin file:**
   ```bash
   nano plugins/mynewplugin/plugin.py
   ```

3. **Configure your plugin:**
   Add your plugin to `config/plugins.yaml`:
   ```yaml
   mynewplugin:
     enabled: true
     config:
       my_setting: "value"
       timeout: 30
   ```

4. **Modify the class:**
   - Change class name from `ExamplePlugin` to `MyNewPlugin`
   - Update plugin name, commands, and functionality
   - Implement configuration loading in `initialize()`

5. **Test your plugin:**
   The bot will automatically discover and load your new plugin with hot reloading!

#### 5. Advanced Plugin Features

**File Operations:**
```python
# Upload files to Matrix rooms
await bot_instance.send_file(room_id, file_path, filename, mimetype)

# Send messages
await bot_instance.send_message(room_id, "Hello!")
```

**Database Integration:**
```python
# Access database if available
if bot_instance.db_enabled:
    await bot_instance.store_message_in_db(room_id, event_id, sender, type, content)
```

**Plugin Communication:**
```python
# Access other plugins
other_plugin = bot_instance.plugin_manager.plugins.get("otherplugin")
if other_plugin and other_plugin.enabled:
    # Use other plugin functionality
```

### Plugin Management Commands

- `bot: plugins` - List all loaded plugins and their status
- `bot: reload <plugin_name>` - Reload a specific plugin
- `bot: enable <plugin_name>` - Enable a disabled plugin  
- `bot: disable <plugin_name>` - Disable a running plugin

### Plugin Configuration

Plugins can be configured via the `config/plugins.yaml` file. This allows you to:
- ✅ Enable/disable plugins globally
- ⚙️ Configure plugin-specific settings
- 🎛️ Override default plugin behavior

#### Configuration File Structure (`config/plugins.yaml`)

```yaml
youtube:
  enabled: true
  config:
    max_cached_per_room: 5
    chunk_size: 8000

ai:
  enabled: true
  config:
    model: "cognitivecomputations/dolphin3.0-mistral-24b:free"
    temperature: 0.3
    max_tokens: 500

database:
  enabled: true
  config:
    timeout: 30

core:
  enabled: true
  config:
    debug_enabled: true

example:
  enabled: false  # Disabled by default - skeleton template
  config:
    demo_mode: true
    max_echo_length: 1000
```

#### Configuration Usage in Plugins

Plugins can access their configuration through the bot config system:

```python
from config import BotConfig

class MyPlugin(BotPlugin):
    async def initialize(self, bot_instance) -> bool:
        # Load bot configuration
        config = BotConfig()
        
        # Check if plugin is enabled in config
        if not config.is_plugin_enabled(self.name):
            self.enabled = False
            return True
        
        # Get plugin-specific configuration
        plugin_config = config.get_plugin_config(self.name)
        self.timeout = plugin_config.get("timeout", 30)
        self.max_items = plugin_config.get("max_items", 10)
        
        return True
```

#### Configuration vs Runtime Management

- **🗂️ YAML Configuration**: Persistent settings that survive bot restarts
- **⚡ Runtime Commands**: Temporary changes via `enable`/`disable` commands
- **🔄 Priority**: Runtime commands override YAML configuration until restart

### Plugin Hot Reloading

The bot automatically watches for changes in plugin files and reloads them without requiring a restart. Simply save your plugin file and the changes will take effect immediately!

## Testing

The project includes comprehensive test suites for both main modules and runs in a Docker container environment.

### Prerequisites for Testing

- Docker and Docker Compose installed
- The boo_bot Docker container built and running

### Building the Docker Container

```bash
# Build the Docker container (includes test dependencies)
docker-compose -f boo_bot/docker-compose.yml build

# Or rebuild without cache if needed
docker-compose -f boo_bot/docker-compose.yml build --no-cache
```

### Running Tests

The project includes a dedicated test service in docker-compose for easy test execution. You can run tests using either the new test service or the traditional exec approach.

#### Using the Test Service (Recommended)

```bash
# Run all tests using the dedicated test service
docker-compose --profile test up boo_bot_tests

# Run tests as a one-off command (preferred for CI/CD)
docker-compose run --rm boo_bot_tests

# Run tests with custom pytest options
docker-compose run --rm boo_bot_tests python -m pytest tests/ -v --tb=short

# Run specific test files
docker-compose run --rm boo_bot_tests python -m pytest tests/test_api_client.py -v
docker-compose run --rm boo_bot_tests python -m pytest tests/test_boo_bot.py -v

# Run tests with coverage
docker-compose run --rm boo_bot_tests python -m pytest tests/ --cov=boo_bot --cov=api_client --cov-report=html --cov-report=term-missing -v
```

#### Using Exec Commands (Alternative)

If you have the main bot service running, you can also execute tests directly:

```bash
# Run all tests with verbose output
docker-compose -f boo_bot/docker-compose.yml exec -e PYTHONPATH=/app boo_bot pytest /app/tests -v

# Run specific test files
docker-compose -f boo_bot/docker-compose.yml exec -e PYTHONPATH=/app boo_bot pytest /app/tests/test_api_client.py -v
docker-compose -f boo_bot/docker-compose.yml exec -e PYTHONPATH=/app boo_bot pytest /app/tests/test_boo_bot.py -v

# Run tests with coverage
docker-compose -f boo_bot/docker-compose.yml exec -e PYTHONPATH=/app boo_bot pytest /app/tests --cov=boo_bot --cov=api_client --cov-report=html --cov-report=term-missing -v
```

### Test Results

As of the latest run, all tests are passing:
- **37 tests total: 37 passed, 0 failed**
- **21 tests** for API client functionality (`test_api_client.py`)
- **16 tests** for bot functionality (`test_boo_bot.py`)

### Troubleshooting Tests

If tests fail due to Docker caching issues:

1. **Rebuild without cache:**
   ```bash
   docker-compose -f boo_bot/docker-compose.yml build --no-cache
   ```

2. **Copy updated test files manually (if needed):**
   ```bash
   # Copy test file to running container
   docker cp boo_bot/tests/test_boo_bot.py $(docker-compose -f boo_bot/docker-compose.yml ps -q boo_bot):/app/tests/test_boo_bot.py
   ```

3. **Verify test file contents in container:**
   ```bash
   docker-compose -f boo_bot/docker-compose.yml exec boo_bot cat /app/tests/test_boo_bot.py | grep -n "boo.*debug"
   ```

### Test Coverage

Current test coverage as of the latest run:

| Module | Coverage | Lines Covered | Lines Missing |
|--------|----------|---------------|---------------|
| **api_client.py** | **77%** | 106/137 | 31 |
| **boo_bot.py** | **19%** | 211/1120 | 909 |
| **TOTAL** | **25%** | 317/1257 | 940 |

#### Coverage Details

- **api_client.py**: Well-tested with 77% coverage. Missing coverage mainly in error handling edge cases and file upload functionality.
- **boo_bot.py**: Requires significant test expansion (19% coverage). Most Matrix bot functionality, event handlers, and business logic need comprehensive testing.
- **Test files**: Both test suites achieve 100% coverage, indicating thorough test execution.

#### Viewing Detailed Coverage

After running tests with coverage in Docker, you can extract the HTML report:

```bash
# Run tests with coverage using the test service
docker-compose run --rm boo_bot_tests python -m pytest tests/ --cov=boo_bot --cov=api_client --cov-report=html --cov-report=term-missing -v

# Copy coverage report from the test container to host
# Note: Since the test service runs and exits, you'll need to run a temporary container to copy files
docker-compose run --rm -v $(pwd)/boo_bot/coverage:/app/coverage_output boo_bot_tests sh -c "python -m pytest tests/ --cov=boo_bot --cov=api_client --cov-report=html --cov-report=term-missing -v && cp -r htmlcov /app/coverage_output/"

# Open the coverage report in your browser
open boo_bot/coverage/htmlcov/index.html  # On macOS
xdg-open boo_bot/coverage/htmlcov/index.html  # On Linux
start boo_bot/coverage/htmlcov/index.html  # On Windows
```

Alternatively, using the exec approach if the main service is running:

```bash
# Run tests with coverage using exec
docker-compose -f boo_bot/docker-compose.yml exec -e PYTHONPATH=/app boo_bot pytest /app/tests --cov=boo_bot --cov=api_client --cov-report=html --cov-report=term-missing -v

# Copy coverage report from container to host
docker cp $(docker-compose -f boo_bot/docker-compose.yml ps -q boo_bot):/app/htmlcov ./boo_bot/coverage/
```

The HTML report provides:
- Line-by-line coverage visualization
- Interactive file navigation
- Detailed missing line identification
- Function and class coverage statistics

### Test Structure

- `tests/test_api_client.py`: Tests for the ChatDatabaseClient class including HTTP operations, error handling, and async functionality
- `tests/test_boo_bot.py`: Tests for the DebugMatrixBot class including Matrix event handling and bot operations

## Technologies Used

*   [matrix-nio](https://github.com/matrix-nio/matrix-nio) - Python Matrix client library
*   [aiohttp](https://docs.aiohttp.org/en/stable/) - Asynchronous HTTP client/server framework (used by `api_client.py`)
*   [httpx](https://www.python-httpx.org/) - A next-generation HTTP client for Python (used for Matrix homeserver requests)
*   [python-dotenv](https://pypi.org/project/python-dotenv/) - For managing environment variables
*   [cryptography](https://cryptography.io/en/latest/) - For media decryption
*   [yt-dlp](https://github.com/yt-dlp/yt-dlp) - For YouTube video processing (subtitles, titles)
*   [OpenRouter.ai](https://openrouter.ai/) - For AI model integration (e.g., summarization, advice)
*   [NIST Randomness Beacon](https://beacon.nist.gov/) - For quantum-enhanced randomness

## Contributing

Contributions are welcome! Please feel free to open issues or submit pull requests.

## License

This project is licensed under the MIT License - see the LICENSE.md file for details (if applicable).

## Acknowledgements

This project was partially generated by Claude 4 Sonnet and Gemini 2.5 Flash.

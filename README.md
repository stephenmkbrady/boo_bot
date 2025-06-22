# Boo Bot

This repository contains the `boo_bot` project, a proof-of-concept Matrix chatbot designed to interact with a Matrix homeserver. It uses the `matrix-nio` library for Matrix communication and an external API client (`api_client.py`) for database interactions.

**Note:** This project is currently a development proof of concept and is not production-ready.

## Features

*   **Matrix Homeserver Integration:** Communicates with a Matrix homeserver to send and receive messages.
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

The API will be accessible at `http://localhost:8000`.

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

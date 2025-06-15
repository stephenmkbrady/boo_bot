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

The project includes comprehensive test suites for both main modules.

### Running Tests

To run the test suite:

```bash
# Activate virtual environment
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`

# Install test dependencies (if not already installed)
pip install pytest pytest-asyncio pytest-cov

# Run tests
PYTHONPATH=. ../venv/bin/pytest tests/

# Run tests with coverage
PYTHONPATH=. ../venv/bin/pytest --cov=boo_bot --cov=api_client --cov-report=html --cov-report=term-missing tests/
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

After running tests with coverage, open the HTML report:

```bash
# Open the coverage report in your browser
open boo_bot/coverage/htmlcov/index.html  # On macOS
xdg-open boo_bot/coverage/htmlcov/index.html  # On Linux
start boo_bot/coverage/htmlcov/index.html  # On Windows
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

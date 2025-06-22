import pytest
import asyncio
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch, ANY
from datetime import datetime, timedelta
from boo_bot import DebugMatrixBot
from youtube_handler import create_Youtube_url

# Mock the nio.AsyncClient and other external dependencies
@pytest.fixture
def mock_nio_asyncclient():
    with patch('boo_bot.AsyncClient') as MockAsyncClient:
        mock_client_instance = MockAsyncClient.return_value
        mock_client_instance.login = AsyncMock(return_value=MagicMock(device_id="test_device", access_token="test_token"))
        mock_client_instance.join = AsyncMock(return_value=MagicMock(room_id="!test:matrix.org"))
        mock_client_instance.room_send = AsyncMock()
        mock_client_instance.sync_forever = AsyncMock()
        mock_client_instance.close = AsyncMock()
        mock_client_instance.olm = MagicMock() # Mock olm attribute
        mock_client_instance.olm.account = MagicMock() # Mock olm.account
        mock_client_instance.olm.account.generate_one_time_keys = MagicMock() # Mock generate_one_time_keys
        mock_client_instance.keys_upload = AsyncMock()
        mock_client_instance.keys_query = AsyncMock(return_value=MagicMock(device_keys={}))
        mock_client_instance.verify_device = MagicMock()
        yield mock_client_instance

# Mock the api_client.ChatDatabaseClient
@pytest.fixture
def mock_chat_database_client():
    with patch('boo_bot.ChatDatabaseClient') as MockChatDatabaseClient:
        mock_db_client_instance = MockChatDatabaseClient.return_value
        mock_db_client_instance.store_message = AsyncMock(return_value={"id": 123})
        mock_db_client_instance.health_check = AsyncMock(return_value=True)
        mock_db_client_instance.get_database_stats = AsyncMock(return_value={"total_messages": 10, "total_media_files": 2})
        mock_db_client_instance.upload_media = AsyncMock(return_value={"success": True})
        yield mock_db_client_instance

# Mock os.getenv to control environment variables
@pytest.fixture
def mock_env_vars():
    with patch('os.getenv') as mock_getenv:
        mock_getenv.side_effect = lambda key, default=None: {
            "HOMESERVER": "https://matrix.org",
            "USER_ID": "@testuser:matrix.org",
            "PASSWORD": "testpassword",
            "ROOM_ID": "!test:matrix.org",
            "DATABASE_API_URL": "http://localhost:8000",
            "DATABASE_API_KEY": "test_api_key",
            "OPENROUTER_API_KEY": "test_openrouter_key"
        }.get(key, default)
        yield

# Fixture for a bot instance with mocked dependencies
@pytest_asyncio.fixture
async def bot_instance(mock_nio_asyncclient, mock_chat_database_client, mock_env_vars):
    bot = DebugMatrixBot(
        homeserver="https://matrix.org",
        user_id="@testuser:matrix.org",
        password="testpassword",
        device_name="TestBot"
    )
    # Manually set db_enabled to True since _init_database_client is called in __init__
    # and we want to ensure it's enabled for tests that rely on it.
    bot.db_enabled = True
    bot.db_client = mock_chat_database_client
    
    # Set the display name for command processing - this is what the tests expect
    bot.current_display_name = "boo"
    
    yield bot

# Test for parse_vtt
def test_parse_vtt():
    from youtube_handler import YouTubeProcessor
    vtt_content = """WEBVTT

00:00:01.000 --> 00:00:03.000
Hello world.

00:00:04.000 --> 00:00:06.000
This is a test.

00:00:07.000 --> 00:00:09.000
<c.red>Red text</c> and <b>bold</b> text.
"""
    expected_text = "Hello world. This is a test. Red text and bold text."
    processor = YouTubeProcessor()
    assert processor.parse_vtt(vtt_content) == expected_text

def test_parse_vtt_empty():
    from youtube_handler import YouTubeProcessor
    vtt_content = "WEBVTT\n\n"
    processor = YouTubeProcessor()
    assert processor.parse_vtt(vtt_content) == ""

def test_parse_vtt_no_text():
    from youtube_handler import YouTubeProcessor
    vtt_content = """WEBVTT

00:00:01.000 --> 00:00:03.000
"""
    processor = YouTubeProcessor()
    assert processor.parse_vtt(vtt_content) == ""

# Test for create_Youtube_url
def test_create_youtube_url_with_artist():
    song_text = '"Bohemian Rhapsody" by Queen'
    expected_url = "https://www.youtube.com/results?search_query=Queen+Bohemian+Rhapsody"
    assert create_Youtube_url(song_text) == expected_url

def test_create_youtube_url_without_artist():
    song_text = "Imagine"
    expected_url = "https://www.youtube.com/results?search_query=Imagine"
    assert create_Youtube_url(song_text) == expected_url

def test_create_youtube_url_special_chars():
    song_text = "Song & Dance (Live!)"
    expected_url = "https://www.youtube.com/results?search_query=Song+%26+Dance+%28Live%21%29"
    assert create_Youtube_url(song_text) == expected_url

# Test for handle_bot_command (basic)
@pytest.mark.asyncio
async def test_handle_bot_command_debug(bot_instance, mock_nio_asyncclient):
    mock_room = MagicMock()
    mock_room.room_id = "!test:matrix.org"
    mock_room.name = "Test Room"
    mock_room.encrypted = False
    mock_room.users = {"@testuser:matrix.org": MagicMock()} # Mock users for len()

    mock_event = MagicMock()
    mock_event.sender = "@otheruser:matrix.org"
    mock_event.body = "boo: debug"
    mock_event.relates_to = None # Not an edit

    await bot_instance.handle_bot_command(mock_room, mock_event, "boo: debug")

    mock_nio_asyncclient.room_send.assert_called()
    args, kwargs = mock_nio_asyncclient.room_send.call_args
    assert kwargs['room_id'] == "!test:matrix.org"
    assert "SIMPLIFIED DEBUG INFO" in kwargs['content']['body']

@pytest.mark.asyncio
async def test_handle_bot_command_talk(bot_instance, mock_nio_asyncclient):
    mock_room = MagicMock()
    mock_room.room_id = "!test:matrix.org"
    mock_event = MagicMock()
    mock_event.sender = "@otheruser:matrix.org"
    mock_event.body = "boo: talk"
    mock_event.relates_to = None

    await bot_instance.handle_bot_command(mock_room, mock_event, "boo: talk")

    mock_nio_asyncclient.room_send.assert_called_once_with(
        room_id="!test:matrix.org",
        message_type="m.room.message",
        content={"msgtype": "m.text", "body": "Hello! I'm boo - the simplified bot with proper encrypted media decryption!"},
        ignore_unverified_devices=True
    )

@pytest.mark.asyncio
async def test_handle_bot_command_unknown(bot_instance, mock_nio_asyncclient):
    mock_room = MagicMock()
    mock_room.room_id = "!test:matrix.org"
    mock_event = MagicMock()
    mock_event.sender = "@otheruser:matrix.org"
    mock_event.body = "boo: unknown"
    mock_event.relates_to = None

    await bot_instance.handle_bot_command(mock_room, mock_event, "boo: unknown")

    mock_nio_asyncclient.room_send.assert_called_once_with(
        room_id="!test:matrix.org",
        message_type="m.room.message",
        content={"msgtype": "m.text", "body": "Unknown command. Try 'boo: help' or 'boo: debug'"},
        ignore_unverified_devices=True
    )

# Test for store_message_in_db
@pytest.mark.asyncio
async def test_store_message_in_db_enabled(bot_instance, mock_chat_database_client):
    room_id = "!test:matrix.org"
    event_id = "$event123"
    sender = "@testuser:matrix.org"
    message_type = "text"
    content = "Hello from test"
    
    result = await bot_instance.store_message_in_db(room_id, event_id, sender, message_type, content)
    
    mock_chat_database_client.store_message.assert_called_once_with(
        room_id=room_id,
        event_id=event_id,
        sender=sender,
        message_type=message_type,
        content=content,
        timestamp=ANY # Use ANY for timestamp as it's dynamic
    )
    assert result == {"id": 123}

@pytest.mark.asyncio
async def test_store_message_in_db_disabled(bot_instance, mock_chat_database_client):
    bot_instance.db_enabled = False # Disable DB for this test
    
    result = await bot_instance.store_message_in_db("room", "event", "sender", "type", "content")
    
    mock_chat_database_client.store_message.assert_not_called()
    assert result is None

# Test for handle_db_health_check
@pytest.mark.asyncio
async def test_handle_db_health_check_healthy(bot_instance, mock_nio_asyncclient, mock_chat_database_client):
    mock_chat_database_client.health_check.return_value = True
    mock_room_id = "!test:matrix.org"
    
    await bot_instance.handle_db_health_check(mock_room_id)
    
    mock_chat_database_client.health_check.assert_called_once()
    mock_nio_asyncclient.room_send.assert_called()
    args, kwargs = mock_nio_asyncclient.room_send.call_args
    assert "Database Health: HEALTHY" in kwargs['content']['body']

@pytest.mark.asyncio
async def test_handle_db_health_check_unhealthy(bot_instance, mock_nio_asyncclient, mock_chat_database_client):
    mock_chat_database_client.health_check.return_value = False
    mock_room_id = "!test:matrix.org"
    
    await bot_instance.handle_db_health_check(mock_room_id)
    
    mock_chat_database_client.health_check.assert_called_once()
    mock_nio_asyncclient.room_send.assert_called()
    args, kwargs = mock_nio_asyncclient.room_send.call_args
    assert "Database Health: UNHEALTHY" in kwargs['content']['body']

# Test for handle_db_stats
@pytest.mark.asyncio
async def test_handle_db_stats_success(bot_instance, mock_nio_asyncclient, mock_chat_database_client):
    mock_chat_database_client.get_database_stats.return_value = {
        "total_messages": 100,
        "total_media_files": 10,
        "total_size_mb": 50.5,
        "updated_at": "2023-01-01T12:00:00Z"
    }
    mock_room_id = "!test:matrix.org"
    
    await bot_instance.handle_db_stats(mock_room_id)
    
    mock_chat_database_client.get_database_stats.assert_called_once()
    mock_nio_asyncclient.room_send.assert_called()
    args, kwargs = mock_nio_asyncclient.room_send.call_args
    assert "📝 **Messages:** 100" in kwargs['content']['body']
    assert "📁 **Media Files:** 10" in kwargs['content']['body']
    assert "💾 **Size:** 50.50 MB" in kwargs['content']['body']

@pytest.mark.asyncio
async def test_handle_db_stats_failure(bot_instance, mock_nio_asyncclient, mock_chat_database_client):
    mock_chat_database_client.get_database_stats.return_value = None
    mock_room_id = "!test:matrix.org"
    
    await bot_instance.handle_db_stats(mock_room_id)
    
    mock_chat_database_client.get_database_stats.assert_called_once()
    mock_nio_asyncclient.room_send.assert_called()
    args, kwargs = mock_nio_asyncclient.room_send.call_args
    assert "Failed to retrieve database statistics" in kwargs['content']['body']

# Test for send_message
@pytest.mark.asyncio
async def test_send_message(bot_instance, mock_nio_asyncclient, mock_chat_database_client):
    mock_nio_asyncclient.room_send.return_value = MagicMock(event_id="$event456")
    mock_room_id = "!test:matrix.org"
    message_content = "Test message"
    
    await bot_instance.send_message(mock_room_id, message_content)
    
    mock_nio_asyncclient.room_send.assert_called_once_with(
        room_id=mock_room_id,
        message_type="m.room.message",
        content={"msgtype": "m.text", "body": message_content},
        ignore_unverified_devices=True
    )
    mock_chat_database_client.store_message.assert_called_once()
    args, kwargs = mock_chat_database_client.store_message.call_args
    assert kwargs['event_id'] == "$event456"
    assert kwargs['content'] == message_content
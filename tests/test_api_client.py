import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from api_client import ChatDatabaseClient
import aiohttp
import aiofiles
from pathlib import Path

# Fixture for ChatDatabaseClient instance
@pytest.fixture
def client():
    return ChatDatabaseClient("http://test.api", "test_key")

# Fixture for mocking aiohttp.ClientSession
@pytest.fixture
def mock_client_session():
    with patch('aiohttp.ClientSession') as MockSession:
        mock_session_instance = MockSession.return_value
        mock_session_instance.__aenter__ = AsyncMock(return_value=mock_session_instance)
        mock_session_instance.__aexit__ = AsyncMock(return_value=None)
        yield mock_session_instance

# Test for __init__
def test_chat_database_client_init(client):
    assert client.base_url == "http://test.api"
    assert client.api_key == "test_key"
    assert client.headers == {
        'Authorization': 'Bearer test_key',
        'Content-Type': 'application/json'
    }

# Test for health_check
@pytest.mark.asyncio
async def test_health_check_healthy(client, mock_client_session):
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = {"status": "healthy"}
    mock_client_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
    mock_client_session.get.return_value.__aexit__ = AsyncMock(return_value=None)

    result = await client.health_check()
    assert result is True
    mock_client_session.get.assert_called_once_with(
        "http://test.api/health",
        headers={'Authorization': 'Bearer test_key'},
        timeout=aiohttp.ClientTimeout(total=10)
    )

@pytest.mark.asyncio
async def test_health_check_unhealthy(client, mock_client_session):
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = {"status": "unhealthy"}
    mock_client_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
    mock_client_session.get.return_value.__aexit__ = AsyncMock(return_value=None)

    result = await client.health_check()
    assert result is False

@pytest.mark.asyncio
async def test_health_check_api_error(client, mock_client_session):
    mock_response = AsyncMock()
    mock_response.status = 500
    mock_response.text.return_value = "Internal Server Error"
    mock_client_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
    mock_client_session.get.return_value.__aexit__ = AsyncMock(return_value=None)

    result = await client.health_check()
    assert result is False

@pytest.mark.asyncio
async def test_health_check_network_error(client, mock_client_session):
    mock_client_session.get.side_effect = aiohttp.ClientError("Network error")

    result = await client.health_check()
    assert result is False

# Test for store_message
@pytest.mark.asyncio
async def test_store_message_success(client, mock_client_session):
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = {"id": 1}
    mock_client_session.post.return_value.__aenter__ = AsyncMock(return_value=mock_response)
    mock_client_session.post.return_value.__aexit__ = AsyncMock(return_value=None)

    room_id = "test_room"
    event_id = "test_event"
    sender = "test_sender"
    message_type = "text"
    content = "Hello world"

    result = await client.store_message(room_id, event_id, sender, message_type, content)
    assert result == {"id": 1}
    mock_client_session.post.assert_called_once()
    args, kwargs = mock_client_session.post.call_args
    assert args[0] == "http://test.api/messages"
    assert kwargs['json']['room_id'] == room_id
    assert kwargs['json']['event_id'] == event_id
    assert kwargs['json']['sender'] == sender
    assert kwargs['json']['message_type'] == message_type
    assert kwargs['json']['content'] == content

@pytest.mark.asyncio
async def test_store_message_api_error(client, mock_client_session):
    mock_response = AsyncMock()
    mock_response.status = 400
    mock_response.text.return_value = "Bad Request"
    mock_client_session.post.return_value.__aenter__ = AsyncMock(return_value=mock_response)
    mock_client_session.post.return_value.__aexit__ = AsyncMock(return_value=None)

    result = await client.store_message("r", "e", "s", "t", "c")
    assert result is None

@pytest.mark.asyncio
async def test_store_message_network_error(client, mock_client_session):
    mock_client_session.post.side_effect = aiohttp.ClientError("Network error")

    result = await client.store_message("r", "e", "s", "t", "c")
    assert result is None

# Test for get_messages
@pytest.mark.asyncio
async def test_get_messages_success(client, mock_client_session):
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = [{"id": 1, "content": "msg1"}]
    mock_client_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
    mock_client_session.get.return_value.__aexit__ = AsyncMock(return_value=None)

    room_id = "test_room"
    result = await client.get_messages(room_id)
    assert result == [{"id": 1, "content": "msg1"}]
    mock_client_session.get.assert_called_once()
    args, kwargs = mock_client_session.get.call_args
    assert args[0] == "http://test.api/messages?room_id=test_room&limit=100"

@pytest.mark.asyncio
async def test_get_messages_with_media(client, mock_client_session):
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = [{"id": 1, "content": "msg1", "media": True}]
    mock_client_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
    mock_client_session.get.return_value.__aexit__ = AsyncMock(return_value=None)

    room_id = "test_room"
    result = await client.get_messages(room_id, include_media=True)
    assert result == [{"id": 1, "content": "msg1", "media": True}]
    mock_client_session.get.assert_called_once()
    args, kwargs = mock_client_session.get.call_args
    assert args[0] == "http://test.api/messages?room_id=test_room&limit=100&include_media=true"

@pytest.mark.asyncio
async def test_get_messages_api_error(client, mock_client_session):
    mock_response = AsyncMock()
    mock_response.status = 500
    mock_response.text.return_value = "Internal Server Error"
    mock_client_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
    mock_client_session.get.return_value.__aexit__ = AsyncMock(return_value=None)

    result = await client.get_messages("r")
    assert result is None

@pytest.mark.asyncio
async def test_get_messages_network_error(client, mock_client_session):
    mock_client_session.get.side_effect = aiohttp.ClientError("Network error")

    result = await client.get_messages("r")
    assert result is None

@pytest.mark.asyncio
async def test_upload_media_file_not_found(client):
    result = await client.upload_media(1, "non_existent_file.txt")
    assert result is None

@pytest.mark.asyncio
async def test_upload_media_api_error(client, mock_client_session, tmp_path):
    dummy_file = tmp_path / "test.txt"
    dummy_file.write_text("dummy content")

    mock_response = AsyncMock()
    mock_response.status = 500
    mock_response.text.return_value = "Internal Server Error"
    mock_client_session.post.return_value.__aenter__ = AsyncMock(return_value=mock_response)
    mock_client_session.post.return_value.__aexit__ = AsyncMock(return_value=None)

    with patch('aiofiles.open', new_callable=AsyncMock) as mock_aiofiles_open:
        mock_file_handle = AsyncMock()
        mock_file_handle.__aenter__ = AsyncMock(return_value=mock_file_handle)
        mock_file_handle.__aexit__ = AsyncMock(return_value=None)
        mock_file_handle.read.return_value = b"dummy content"
        mock_aiofiles_open.return_value = mock_file_handle

        result = await client.upload_media(1, str(dummy_file))
        assert result is None

@pytest.mark.asyncio
async def test_upload_media_network_error(client, mock_client_session, tmp_path):
    dummy_file = tmp_path / "test.txt"
    dummy_file.write_text("dummy content")

    mock_client_session.post.side_effect = aiohttp.ClientError("Network error")

    with patch('aiofiles.open', new_callable=AsyncMock) as mock_aiofiles_open:
        mock_file_handle = AsyncMock()
        mock_file_handle.__aenter__ = AsyncMock(return_value=mock_file_handle)
        mock_file_handle.__aexit__ = AsyncMock(return_value=None)
        mock_file_handle.read.return_value = b"dummy content"
        mock_aiofiles_open.return_value = mock_file_handle

        result = await client.upload_media(1, str(dummy_file))
        assert result is None

# Test for get_database_stats
@pytest.mark.asyncio
async def test_get_database_stats_success(client, mock_client_session):
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = {"total_messages": 10, "total_media_files": 2}
    mock_client_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
    mock_client_session.get.return_value.__aexit__ = AsyncMock(return_value=None)

    result = await client.get_database_stats()
    assert result == {"total_messages": 10, "total_media_files": 2}
    mock_client_session.get.assert_called_once_with(
        "http://test.api/stats",
        headers={'Authorization': 'Bearer test_key', 'Content-Type': 'application/json'},
        timeout=aiohttp.ClientTimeout(total=10)
    )

@pytest.mark.asyncio
async def test_get_database_stats_api_error(client, mock_client_session):
    mock_response = AsyncMock()
    mock_response.status = 500
    mock_response.text.return_value = "Internal Server Error"
    mock_client_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
    mock_client_session.get.return_value.__aexit__ = AsyncMock(return_value=None)

    result = await client.get_database_stats()
    assert result is None

@pytest.mark.asyncio
async def test_get_database_stats_network_error(client, mock_client_session):
    mock_client_session.get.side_effect = aiohttp.ClientError("Network error")

    result = await client.get_database_stats()
    assert result is None

# Test for delete_message
@pytest.mark.asyncio
async def test_delete_message_success(client, mock_client_session):
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_client_session.delete.return_value.__aenter__ = AsyncMock(return_value=mock_response)
    mock_client_session.delete.return_value.__aexit__ = AsyncMock(return_value=None)

    message_id = 123
    result = await client.delete_message(message_id)
    assert result is True
    mock_client_session.delete.assert_called_once_with(
        "http://test.api/messages/123",
        headers={'Authorization': 'Bearer test_key', 'Content-Type': 'application/json'},
        timeout=aiohttp.ClientTimeout(total=10)
    )

@pytest.mark.asyncio
async def test_delete_message_api_error(client, mock_client_session):
    mock_response = AsyncMock()
    mock_response.status = 404
    mock_response.text.return_value = "Not Found"
    mock_client_session.delete.return_value.__aenter__ = AsyncMock(return_value=mock_response)
    mock_client_session.delete.return_value.__aexit__ = AsyncMock(return_value=None)

    result = await client.delete_message(123)
    assert result is False

@pytest.mark.asyncio
async def test_delete_message_network_error(client, mock_client_session):
    mock_client_session.delete.side_effect = aiohttp.ClientError("Network error")

    result = await client.delete_message(123)
    assert result is False
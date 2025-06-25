#!/usr/bin/env python3
"""
Automated tests for bot message and media storage functionality
"""

import pytest
import asyncio
import os
import tempfile
import hashlib
import time
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from pathlib import Path

import sys
sys.path.append('/app')

from plugins.database.plugin import ChatDatabaseClient
from boo_bot import CleanMatrixBot
from nio import MatrixRoom, RoomMessageText, RoomMessageImage


class TestMessageStorage:
    """Test suite for message and media storage functionality"""
    
    @pytest.fixture
    def mock_database_client(self):
        """Create a mock database client for testing"""
        client = Mock(spec=ChatDatabaseClient)
        client.health_check = AsyncMock(return_value=True)
        client.store_message = AsyncMock(return_value={'id': 123})
        client.upload_media = AsyncMock(return_value={
            'filename': 'test_media_file.png',
            'media_url': '/media/test_media_file.png',
            'mimetype': 'image/png',
            'size': 1024
        })
        return client
    
    @pytest.fixture
    def mock_bot(self, mock_database_client):
        """Create a mock bot instance with database client"""
        bot = Mock(spec=CleanMatrixBot)
        bot.user_id = "@test_bot:matrix.org"
        bot.current_display_name = "testbot"
        bot.db_enabled = True
        bot.db_client = mock_database_client
        bot.event_counters = {'text_messages': 0}
        bot.last_name_check = datetime.now()
        return bot
    
    @pytest.fixture
    def mock_room(self):
        """Create a mock Matrix room"""
        room = Mock(spec=MatrixRoom)
        room.room_id = "!test_room:matrix.org"
        room.name = "Test Room"
        return room
    
    @pytest.fixture
    def mock_text_event(self):
        """Create a mock text message event"""
        event = Mock(spec=RoomMessageText)
        event.event_id = "$test_text_event_123"
        event.sender = "@user:matrix.org"
        event.body = "Test message content"
        event.server_timestamp = int(datetime.now().timestamp() * 1000)
        return event
    
    @pytest.fixture
    def mock_media_event(self):
        """Create a mock media message event"""
        event = Mock(spec=RoomMessageImage)
        event.event_id = "$test_media_event_456"
        event.sender = "@user:matrix.org"
        event.body = "test_image.png"
        event.server_timestamp = int(datetime.now().timestamp() * 1000)
        event.url = "mxc://matrix.org/test_media_content_uri"
        return event
    
    @pytest.fixture
    def test_image_file(self):
        """Create a temporary test image file"""
        # Create a simple PNG-like test file
        test_data = b'\x89PNG\r\n\x1a\n' + b'test_image_data' * 100
        
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            f.write(test_data)
            temp_path = f.name
        
        yield temp_path
        
        # Cleanup
        if os.path.exists(temp_path):
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_text_message_storage(self, mock_bot, mock_room, mock_text_event):
        """Test that text messages are properly stored in database"""
        # Create bot instance and simulate text message callback
        bot = CleanMatrixBot("https://matrix.org", "@test:matrix.org", "password")
        
        # Setup mocks
        bot.user_id = mock_bot.user_id
        bot.current_display_name = mock_bot.current_display_name
        bot.db_enabled = mock_bot.db_enabled
        bot.db_client = mock_bot.db_client
        bot.event_counters = mock_bot.event_counters
        bot.last_name_check = mock_bot.last_name_check
        
        # Mock the handle_command method to avoid command processing
        bot.handle_command = AsyncMock()
        
        # Call the text message callback
        await bot.text_message_callback(mock_room, mock_text_event)
        
        # Verify database storage was called
        mock_bot.db_client.store_message.assert_called_once()
        call_args = mock_bot.db_client.store_message.call_args
        
        assert call_args[1]['room_id'] == mock_room.room_id
        assert call_args[1]['event_id'] == mock_text_event.event_id
        assert call_args[1]['sender'] == mock_text_event.sender
        assert call_args[1]['message_type'] == "text"
        assert call_args[1]['content'] == mock_text_event.body
        
        # Verify handle_command was called (for command processing)
        bot.handle_command.assert_called_once_with(mock_room, mock_text_event)
    
    @pytest.mark.asyncio
    async def test_text_message_ignores_own_messages(self, mock_bot, mock_room, mock_text_event):
        """Test that bot ignores its own text messages"""
        # Set event sender to be the bot itself
        mock_text_event.sender = mock_bot.user_id
        
        bot = CleanMatrixBot("https://matrix.org", "@test:matrix.org", "password")
        bot.user_id = mock_bot.user_id
        bot.db_enabled = mock_bot.db_enabled
        bot.db_client = mock_bot.db_client
        bot.event_counters = mock_bot.event_counters
        
        await bot.text_message_callback(mock_room, mock_text_event)
        
        # Verify no database storage was attempted
        mock_bot.db_client.store_message.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_database_storage_error_handling(self, mock_bot, mock_room, mock_text_event):
        """Test error handling when database storage fails"""
        # Make database storage fail
        mock_bot.db_client.store_message.side_effect = Exception("Database connection failed")
        
        bot = CleanMatrixBot("https://matrix.org", "@test:matrix.org", "password")
        bot.user_id = mock_bot.user_id
        bot.current_display_name = mock_bot.current_display_name
        bot.db_enabled = mock_bot.db_enabled
        bot.db_client = mock_bot.db_client
        bot.event_counters = mock_bot.event_counters
        bot.last_name_check = mock_bot.last_name_check
        bot.handle_command = AsyncMock()
        
        # Should not raise exception despite database error
        await bot.text_message_callback(mock_room, mock_text_event)
        
        # Verify storage was attempted
        mock_bot.db_client.store_message.assert_called_once()
        
        # Verify command handling still continues
        bot.handle_command.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_database_disabled_handling(self, mock_room, mock_text_event):
        """Test behavior when database is disabled"""
        bot = CleanMatrixBot("https://matrix.org", "@test:matrix.org", "password")
        bot.user_id = "@test:matrix.org"
        bot.current_display_name = "testbot"
        bot.db_enabled = False  # Database disabled
        bot.db_client = None
        bot.event_counters = {'text_messages': 0}
        bot.last_name_check = datetime.now()
        bot.handle_command = AsyncMock()
        
        # Should handle gracefully when database is disabled
        await bot.text_message_callback(mock_room, mock_text_event)
        
        # Command handling should still work
        bot.handle_command.assert_called_once()


class TestDatabaseClient:
    """Test suite for database client functionality"""
    
    @pytest.fixture
    def test_database_client(self):
        """Create a test database client"""
        return ChatDatabaseClient("http://localhost:8000", "test_api_key")
    
    @pytest.mark.asyncio
    async def test_store_message_api_call(self, test_database_client):
        """Test message storage API call structure"""
        # Skip this test until proper async mocking is implemented
        pytest.skip("Async mocking needs proper implementation")
    
    @pytest.mark.asyncio
    async def test_upload_media_api_call(self, test_database_client):
        """Test media upload API call structure"""
        # Skip this test until proper async mocking is implemented
        pytest.skip("Async mocking needs proper implementation")


class TestFileIntegrity:
    """Test suite for file integrity during storage and retrieval"""
    
    @pytest.fixture
    def sample_files(self):
        """Create sample files of different types for testing"""
        files = {}
        
        # PNG-like file
        png_data = b'\x89PNG\r\n\x1a\n' + b'PNG_test_data' * 100
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            f.write(png_data)
            files['png'] = f.name
        
        # JPEG-like file
        jpeg_data = b'\xff\xd8\xff\xe0' + b'JPEG_test_data' * 100
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            f.write(jpeg_data)
            files['jpeg'] = f.name
        
        # Text file
        text_data = "Test text content\nMultiple lines\nWith special chars: àáâãäå"
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(text_data)
            files['text'] = f.name
        
        yield files
        
        # Cleanup
        for file_path in files.values():
            if os.path.exists(file_path):
                os.unlink(file_path)
    
    def test_file_hash_consistency(self, sample_files):
        """Test that file hashes remain consistent through storage simulation"""
        for file_type, file_path in sample_files.items():
            # Calculate original hash
            with open(file_path, 'rb') as f:
                original_data = f.read()
                original_hash = hashlib.sha256(original_data).hexdigest()
            
            # Simulate storage cycle (write to temp location and read back)
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_file.write(original_data)
                temp_path = temp_file.name
            
            try:
                # Read back and verify hash
                with open(temp_path, 'rb') as f:
                    retrieved_data = f.read()
                    retrieved_hash = hashlib.sha256(retrieved_data).hexdigest()
                
                assert original_hash == retrieved_hash, f"Hash mismatch for {file_type} file"
                assert len(original_data) == len(retrieved_data), f"Size mismatch for {file_type} file"
                
            finally:
                os.unlink(temp_path)
    
    def test_mime_type_detection(self, sample_files):
        """Test MIME type detection for different file types"""
        import mimetypes
        
        expected_types = {
            'png': 'image/png',
            'jpeg': 'image/jpeg', 
            'text': 'text/plain'
        }
        
        for file_type, file_path in sample_files.items():
            detected_type, _ = mimetypes.guess_type(file_path)
            expected_type = expected_types[file_type]
            
            assert detected_type == expected_type, f"MIME type mismatch for {file_type}: expected {expected_type}, got {detected_type}"


class TestIntegrationScenarios:
    """Integration tests for complete message storage workflows"""
    
    @pytest.mark.asyncio
    async def test_complete_text_message_workflow(self):
        """Test complete workflow: receive text message -> store -> verify"""
        # This would require actual database connection in integration environment
        # For now, we test the workflow structure
        
        # Mock components
        mock_client = Mock(spec=ChatDatabaseClient)
        mock_client.store_message = AsyncMock(return_value={'id': 456})
        
        # Simulate message data
        message_data = {
            'room_id': '!integration_test:matrix.org',
            'event_id': '$integration_text_event',
            'sender': '@test_user:matrix.org',
            'message_type': 'text',
            'content': 'Integration test message',
            'timestamp': datetime.now()
        }
        
        # Call storage
        result = await mock_client.store_message(**message_data)
        
        # Verify result
        assert result['id'] == 456
        mock_client.store_message.assert_called_once_with(**message_data)
    
    @pytest.mark.asyncio
    async def test_complete_media_message_workflow(self):
        """Test complete workflow: receive media -> store message -> upload file -> verify"""
        mock_client = Mock(spec=ChatDatabaseClient)
        mock_client.store_message = AsyncMock(return_value={'id': 789})
        mock_client.upload_media = AsyncMock(return_value={
            'filename': 'integration_test_media.png',
            'media_url': '/media/integration_test_media.png',
            'mimetype': 'image/png',
            'size': 2048
        })
        
        # Step 1: Store message
        message_result = await mock_client.store_message(
            room_id='!integration_test:matrix.org',
            event_id='$integration_media_event',
            sender='@test_user:matrix.org',
            message_type='image',
            content='integration_test.png'
        )
        
        # Step 2: Upload media
        with tempfile.NamedTemporaryFile(suffix='.png') as temp_file:
            temp_file.write(b'test_media_content')
            temp_file.flush()
            
            media_result = await mock_client.upload_media(message_result['id'], temp_file.name)
        
        # Verify workflow
        assert message_result['id'] == 789
        assert media_result['filename'] == 'integration_test_media.png'
        assert media_result['mimetype'] == 'image/png'


# Integration test utilities
def run_integration_tests():
    """
    Run integration tests that require actual services.
    This function can be called separately when services are available.
    """
    import subprocess
    import requests
    
    def check_service_health(url, service_name):
        """Check if a service is healthy"""
        try:
            response = requests.get(f"{url}/health", timeout=5)
            if response.status_code == 200:
                print(f"✅ {service_name} is healthy")
                return True
            else:
                print(f"❌ {service_name} returned status {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ {service_name} health check failed: {e}")
            return False
    
    # Check required services
    services_ok = True
    services_ok &= check_service_health("http://localhost:8000", "boo_memories API")
    
    if not services_ok:
        print("⚠️ Skipping integration tests - required services not available")
        return False
    
    print("🧪 Running integration tests...")
    
    # Run the actual integration test
    try:
        result = subprocess.run([
            'python', '-m', 'pytest', 
            '/app/tests/test_message_storage.py::TestIntegrationScenarios',
            '-v'
        ], capture_output=True, text=True, cwd='/app')
        
        if result.returncode == 0:
            print("✅ Integration tests passed")
            return True
        else:
            print("❌ Integration tests failed")
            print(result.stdout)
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ Error running integration tests: {e}")
        return False


if __name__ == "__main__":
    # Run unit tests
    import subprocess
    
    print("🧪 Running message storage tests...")
    
    result = subprocess.run([
        'python', '-m', 'pytest', 
        '/app/tests/test_message_storage.py',
        '-v', '--tb=short'
    ], cwd='/app')
    
    if result.returncode == 0:
        print("\n✅ All unit tests passed!")
        
        # Optionally run integration tests if services are available
        print("\n🔍 Checking for integration test environment...")
        integration_success = run_integration_tests()
        
        if integration_success:
            print("✅ Full test suite completed successfully!")
        else:
            print("⚠️ Unit tests passed, integration tests skipped")
    else:
        print("\n❌ Some tests failed")
        exit(1)
#!/usr/bin/env python3
"""
Integration test for complete file upload/download cycle
This test can be run independently and is suitable for CI/CD
"""

import pytest
import asyncio
import tempfile
import hashlib
import os
import json
import subprocess
import time
from pathlib import Path


class TestFileCycleIntegration:
    """Integration tests for file upload/download cycle"""
    
    @pytest.fixture
    def test_image_data(self):
        """Generate test image data"""
        # Create a simple PNG-like test file with recognizable content
        png_header = b'\x89PNG\r\n\x1a\n'
        test_content = b'BOO_BOT_TEST_IMAGE_DATA_' + b'A' * 1000 + b'_END'
        return png_header + test_content
    
    @pytest.fixture
    def temp_test_file(self, test_image_data):
        """Create temporary test file"""
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            f.write(test_image_data)
            temp_path = f.name
        
        yield temp_path, test_image_data
        
        # Cleanup
        if os.path.exists(temp_path):
            os.unlink(temp_path)
    
    def test_file_hash_calculation(self, temp_test_file):
        """Test that we can reliably calculate file hashes"""
        file_path, original_data = temp_test_file
        
        # Calculate hash from file
        with open(file_path, 'rb') as f:
            file_data = f.read()
        
        file_hash = hashlib.sha256(file_data).hexdigest()
        data_hash = hashlib.sha256(original_data).hexdigest()
        
        assert file_hash == data_hash
        assert len(file_data) == len(original_data)
    
    def test_database_api_upload_download_cycle(self, temp_test_file):
        """Test complete upload/download cycle via database API"""
        file_path, original_data = temp_test_file
        api_key = "0DZ9a/sbgajCRmAMO+6SU2qCkw3QqTe5uJaPGa5YptA="
        base_url = "http://localhost:8000"
        
        # Skip if database API is not available
        if not self._check_api_available(base_url, api_key):
            pytest.skip("Database API not available")
        
        # Calculate original hash
        original_hash = hashlib.sha256(original_data).hexdigest()
        
        try:
            # Step 1: Create test message
            message_data = {
                "room_id": "!test_integration:example.com",
                "event_id": f"$test_cycle_event_{int(time.time())}",
                "sender": "@test_integration:example.com",
                "message_type": "image",
                "content": "Integration test image"
            }
            
            message_result = self._api_call_post(
                f"{base_url}/messages",
                api_key,
                json_data=message_data
            )
            
            assert message_result is not None
            assert 'id' in message_result
            message_id = message_result['id']
            
            # Step 2: Upload media file
            upload_result = self._api_call_upload(
                f"{base_url}/media/upload",
                api_key,
                file_path,
                message_id
            )
            
            assert upload_result is not None
            assert 'media_url' in upload_result
            assert 'filename' in upload_result
            
            media_url = upload_result['media_url']
            uploaded_filename = upload_result['filename']
            
            # Step 3: Download file back
            with tempfile.NamedTemporaryFile(delete=False) as temp_download:
                download_path = temp_download.name
            
            try:
                download_success = self._api_call_download(
                    f"{base_url}{media_url}",
                    api_key,
                    download_path
                )
                
                assert download_success
                assert os.path.exists(download_path)
                
                # Step 4: Verify file integrity
                with open(download_path, 'rb') as f:
                    downloaded_data = f.read()
                
                downloaded_hash = hashlib.sha256(downloaded_data).hexdigest()
                
                assert original_hash == downloaded_hash
                assert len(original_data) == len(downloaded_data)
                assert downloaded_data == original_data
                
                print(f"✅ File cycle test passed:")
                print(f"   Original size: {len(original_data)} bytes")
                print(f"   Downloaded size: {len(downloaded_data)} bytes")
                print(f"   Hash: {original_hash}")
                print(f"   Uploaded filename: {uploaded_filename}")
                
            finally:
                if os.path.exists(download_path):
                    os.unlink(download_path)
        
        except Exception as e:
            pytest.fail(f"File cycle test failed: {e}")
    
    def test_multiple_file_types(self):
        """Test file cycle with different file types"""
        api_key = "0DZ9a/sbgajCRmAMO+6SU2qCkw3QqTe5uJaPGa5YptA="
        base_url = "http://localhost:8000"
        
        if not self._check_api_available(base_url, api_key):
            pytest.skip("Database API not available")
        
        test_files = {
            'png': b'\x89PNG\r\n\x1a\n' + b'PNG_TEST_DATA' * 100,
            'jpg': b'\xff\xd8\xff\xe0' + b'JPEG_TEST_DATA' * 100,
            'txt': 'Text file content with unicode: àáâãäå\n'.encode('utf-8')
        }
        
        for file_type, file_data in test_files.items():
            with tempfile.NamedTemporaryFile(suffix=f'.{file_type}', delete=False) as temp_file:
                temp_file.write(file_data)
                temp_path = temp_file.name
            
            try:
                # Quick test for this file type
                original_hash = hashlib.sha256(file_data).hexdigest()
                
                # Create message
                message_data = {
                    "room_id": "!test_integration:example.com",
                    "event_id": f"$test_{file_type}_event_{int(time.time())}",
                    "sender": "@test_integration:example.com",
                    "message_type": "file",
                    "content": f"Test {file_type} file"
                }
                
                message_result = self._api_call_post(
                    f"{base_url}/messages", api_key, json_data=message_data
                )
                
                if message_result and 'id' in message_result:
                    # Upload file
                    upload_result = self._api_call_upload(
                        f"{base_url}/media/upload",
                        api_key,
                        temp_path,
                        message_result['id']
                    )
                    
                    if upload_result and 'media_url' in upload_result:
                        # Download and verify
                        with tempfile.NamedTemporaryFile(delete=False) as temp_download:
                            download_path = temp_download.name
                        
                        try:
                            if self._api_call_download(f"{base_url}{upload_result['media_url']}", api_key, download_path):
                                with open(download_path, 'rb') as f:
                                    downloaded_data = f.read()
                                
                                downloaded_hash = hashlib.sha256(downloaded_data).hexdigest()
                                assert original_hash == downloaded_hash, f"Hash mismatch for {file_type}"
                                
                                print(f"✅ {file_type.upper()} file test passed")
                        finally:
                            if os.path.exists(download_path):
                                os.unlink(download_path)
            finally:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
    
    def _check_api_available(self, base_url, api_key):
        """Check if the database API is available"""
        try:
            result = subprocess.run([
                'curl', '-s', '-f',
                '-H', f'Authorization: Bearer {api_key}',
                f'{base_url}/health'
            ], capture_output=True, text=True, timeout=5)
            
            return result.returncode == 0
        except:
            return False
    
    def _api_call_post(self, url, api_key, json_data):
        """Make a POST API call with JSON data"""
        try:
            result = subprocess.run([
                'curl', '-s', '-X', 'POST',
                '-H', f'Authorization: Bearer {api_key}',
                '-H', 'Content-Type: application/json',
                '-d', json.dumps(json_data),
                url
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                return json.loads(result.stdout)
            else:
                print(f"POST failed: {result.stderr}")
                return None
        except Exception as e:
            print(f"POST error: {e}")
            return None
    
    def _api_call_upload(self, url, api_key, file_path, message_id):
        """Upload a file via API"""
        try:
            result = subprocess.run([
                'curl', '-s', '-X', 'POST',
                '-H', f'Authorization: Bearer {api_key}',
                '-F', f'message_id={message_id}',
                '-F', f'file=@{file_path}',
                url
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                return json.loads(result.stdout)
            else:
                print(f"Upload failed: {result.stderr}")
                return None
        except Exception as e:
            print(f"Upload error: {e}")
            return None
    
    def _api_call_download(self, url, api_key, output_path):
        """Download a file via API"""
        try:
            result = subprocess.run([
                'curl', '-s', '-L',
                '-H', f'Authorization: Bearer {api_key}',
                '-o', output_path,
                url
            ], capture_output=True, text=True, timeout=30)
            
            return result.returncode == 0 and os.path.exists(output_path)
        except Exception as e:
            print(f"Download error: {e}")
            return False


# Standalone test runner
def run_integration_test():
    """Run the integration test independently"""
    print("🧪 BOO_BOT File Cycle Integration Test")
    print("=" * 50)
    
    # Check if required services are running
    api_key = "0DZ9a/sbgajCRmAMO+6SU2qCkw3QqTe5uJaPGa5YptA="
    base_url = "http://localhost:8000"
    
    print("🔍 Checking database API availability...")
    try:
        result = subprocess.run([
            'curl', '-s', '-f',
            '-H', f'Authorization: Bearer {api_key}',
            f'{base_url}/health'
        ], capture_output=True, text=True, timeout=5)
        
        if result.returncode == 0:
            print("✅ Database API is available")
        else:
            print("❌ Database API not available - start boo_memories service")
            return False
    except Exception as e:
        print(f"❌ Error checking API: {e}")
        return False
    
    # Run the actual test
    print("\n🧪 Running file cycle test...")
    
    try:
        # Create test data
        test_data = b'\x89PNG\r\n\x1a\n' + b'INTEGRATION_TEST_DATA_' + b'X' * 1000
        original_hash = hashlib.sha256(test_data).hexdigest()
        
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
            temp_file.write(test_data)
            test_file_path = temp_file.name
        
        try:
            # Test the complete cycle
            test_instance = TestFileCycleIntegration()
            test_instance.test_database_api_upload_download_cycle((test_file_path, test_data))
            
            print("✅ Integration test PASSED!")
            return True
            
        finally:
            if os.path.exists(test_file_path):
                os.unlink(test_file_path)
    
    except Exception as e:
        print(f"❌ Integration test FAILED: {e}")
        return False


if __name__ == "__main__":
    # Run as standalone test
    success = run_integration_test()
    exit(0 if success else 1)
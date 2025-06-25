#!/usr/bin/env python3
"""
Final test using your actual test.jpg file through the complete storage cycle
"""

import pytest
import subprocess
import json
import hashlib
import os
import time
import urllib.request
import urllib.parse


@pytest.mark.storage
@pytest.mark.integration
@pytest.mark.slow
def test_with_actual_jpg():
    """Test complete cycle with your actual test.jpg file"""
    print("🧪 FINAL TEST: Using your actual test.jpg file")
    print("=" * 60)
    
    source_file = "/app/test_data/test.jpg"
    output_file = "/app/test_data/test_received.jpg"
    
    if not os.path.exists(source_file):
        print(f"❌ Source file not found: {source_file}")
        return False
    
    # Calculate original file hash
    with open(source_file, 'rb') as f:
        original_data = f.read()
        original_hash = hashlib.sha256(original_data).hexdigest()
        original_size = len(original_data)
    
    print(f"📁 Source file: {source_file}")
    print(f"   Size: {original_size:,} bytes")
    print(f"   Hash: {original_hash}")
    
    # API configuration
    api_key = "0DZ9a/sbgajCRmAMO+6SU2qCkw3QqTe5uJaPGa5YptA="
    base_url = "http://172.17.0.1:8000"
    
    try:
        # Step 1: Check API health
        print(f"\n🏥 Step 1: Checking API health...")
        req = urllib.request.Request(f"{base_url}/health")
        req.add_header("Authorization", f"Bearer {api_key}")
        response = urllib.request.urlopen(req, timeout=5)
        health_data = json.loads(response.read().decode())
        
        if health_data.get('status') != 'healthy':
            print("❌ API is not healthy")
            return False
        
        print("✅ API is healthy")
        
        # Step 2: Create message
        print(f"\n📝 Step 2: Creating message...")
        message_data = {
            "room_id": "!test_real_jpg:example.com",
            "event_id": f"$test_real_jpg_{int(time.time())}",
            "sender": "@test_real_jpg:example.com",
            "message_type": "image",
            "content": "Real test.jpg file upload"
        }
        
        req = urllib.request.Request(
            f"{base_url}/messages",
            data=json.dumps(message_data).encode(),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
        )
        
        response = urllib.request.urlopen(req, timeout=10)
        message_result = json.loads(response.read().decode())
        message_id = message_result.get('id')
        
        if not message_id:
            print("❌ No message ID returned")
            return False
        
        print(f"✅ Created message with ID: {message_id}")
        
        # Step 3: Upload your actual test.jpg
        print(f"\n📤 Step 3: Uploading your test.jpg...")
        
        # For multipart upload, we need to construct the form data manually
        boundary = f"----BOO_BOT_TEST_BOUNDARY_{int(time.time())}"
        
        # Read the test file
        with open(source_file, 'rb') as f:
            file_data = f.read()
        
        # Construct multipart form data
        form_data = []
        
        # Add message_id field
        form_data.append(f'--{boundary}'.encode())
        form_data.append(b'Content-Disposition: form-data; name="message_id"')
        form_data.append(b'')
        form_data.append(str(message_id).encode())
        
        # Add file field
        form_data.append(f'--{boundary}'.encode())
        form_data.append(b'Content-Disposition: form-data; name="file"; filename="test.jpg"')
        form_data.append(b'Content-Type: image/jpeg')
        form_data.append(b'')
        form_data.append(file_data)
        
        # End boundary
        form_data.append(f'--{boundary}--'.encode())
        
        # Join with CRLF
        body = b'\r\n'.join(form_data)
        
        req = urllib.request.Request(
            f"{base_url}/media/upload",
            data=body,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": f"multipart/form-data; boundary={boundary}"
            }
        )
        
        response = urllib.request.urlopen(req, timeout=30)
        upload_result = json.loads(response.read().decode())
        
        media_url = upload_result.get('media_url')
        uploaded_filename = upload_result.get('filename')
        uploaded_size = upload_result.get('size')
        
        if not media_url:
            print("❌ No media URL returned")
            return False
        
        print(f"✅ Upload successful:")
        print(f"   Filename: {uploaded_filename}")
        print(f"   Size: {uploaded_size:,} bytes")
        print(f"   Media URL: {media_url}")
        
        # Step 4: Download as test_received.jpg
        print(f"\n📥 Step 4: Downloading as test_received.jpg...")
        
        req = urllib.request.Request(f"{base_url}{media_url}")
        req.add_header("Authorization", f"Bearer {api_key}")
        response = urllib.request.urlopen(req, timeout=10)
        downloaded_data = response.read()
        
        # Write downloaded data to file
        with open(output_file, 'wb') as f:
            f.write(downloaded_data)
        
        if not os.path.exists(output_file):
            print("❌ Downloaded file not found")
            return False
        
        # Step 5: Verify integrity
        print(f"\n🔍 Step 5: Verifying file integrity...")
        downloaded_hash = hashlib.sha256(downloaded_data).hexdigest()
        downloaded_size = len(downloaded_data)
        
        print(f"📊 Comparison results:")
        print(f"   Original size:   {original_size:,} bytes")
        print(f"   Downloaded size: {downloaded_size:,} bytes")
        print(f"   Original hash:   {original_hash}")
        print(f"   Downloaded hash: {downloaded_hash}")
        
        if original_hash == downloaded_hash and original_size == downloaded_size:
            print(f"\n🎉 SUCCESS: Perfect file integrity!")
            print(f"✅ Your test.jpg was uploaded, stored, and downloaded successfully")
            print(f"✅ File is identical to the original (hash and size match)")
            print(f"✅ test_received.jpg verified successfully")
            print(f"   Location: {output_file}")
            
            # Check file type using Python
            print(f"   File size: {os.path.getsize(output_file):,} bytes")
            
            # Clean up test_received.jpg after verification
            print(f"\n🧹 Cleaning up test_received.jpg...")
            os.unlink(output_file)
            print(f"✅ Cleanup complete")
            
            # Test passed successfully
            assert True, "File integrity test passed"
        else:
            print(f"\n❌ FAILURE: File integrity mismatch")
            if original_size != downloaded_size:
                print(f"   Size mismatch: {original_size} vs {downloaded_size}")
            if original_hash != downloaded_hash:
                print(f"   Hash mismatch")
            
            # Clean up failed test file
            if os.path.exists(output_file):
                print(f"🧹 Cleaning up failed test file...")
                os.unlink(output_file)
            
            assert False, "File integrity test failed - hash or size mismatch"
    
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        
        # Clean up any partially created files
        if os.path.exists(output_file):
            print(f"🧹 Cleaning up partial test file...")
            os.unlink(output_file)
        
        assert False, f"Test failed with exception: {e}"


def main():
    success = test_with_actual_jpg()
    
    if success:
        print(f"\n✅ AUTOMATED TEST READY FOR CI/CD")
        print(f"This test can be integrated into automated testing:")
        print(f"1. ✅ Uses real file data")
        print(f"2. ✅ Tests complete upload/download cycle") 
        print(f"3. ✅ Verifies file integrity")
        print(f"4. ✅ Works with JPEG format")
        print(f"5. ✅ Provides clear pass/fail results")
    else:
        print(f"\n❌ Test needs debugging before automation")
    
    return success


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
#!/usr/bin/env python3
"""
Matrix Chat Database API Client - Simplified Version
Removed membership verification and token management features
"""

import aiohttp
import aiofiles
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

class ChatDatabaseClient:
    """Simplified client for interacting with the Matrix Chat Database API"""
    
    def __init__(self, base_url: str, api_key: str):
        """Initialize the API client with authentication"""
        # Remove trailing slash to prevent double slash issues
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        print(f"✅ ChatDatabaseClient initialized")
        print(f"📡 API Base URL: {self.base_url}")
        print(f"🔑 API Key: {api_key[:10]}...")
    
    async def health_check(self) -> bool:
        """Check if the API server is healthy"""
        try:
            url = f"{self.base_url}/health"
            print(f"🏥 Health check URL: {url}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers={'Authorization': f'Bearer {self.api_key}'},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    print(f"🏥 Health check response: {response.status}")
                    if response.status == 200:
                        result = await response.json()
                        print(f"🏥 Health check result: {result}")
                        return result.get('status') == 'healthy'
                    else:
                        print(f"🏥 Health check failed: {response.status}")
                        return False
                        
        except Exception as e:
            print(f"❌ Health check error: {e}")
            return False
    
    async def store_message(self, room_id: str, event_id: str, sender: str, 
                           message_type: str, content: str = None, 
                           timestamp: datetime = None) -> Optional[Dict[str, Any]]:
        """Store a message in the database"""
        try:
            url = f"{self.base_url}/messages"
            
            data = {
                'room_id': room_id,
                'event_id': event_id,
                'sender': sender,
                'message_type': message_type,
                'content': content or '',
                'timestamp': (timestamp or datetime.now()).isoformat()
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    headers=self.headers,
                    json=data,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        print(f"❌ Store message failed: {response.status} - {error_text}")
                        return None
                        
        except Exception as e:
            print(f"❌ Store message error: {e}")
            return None
    
    async def get_messages(self, room_id: str, limit: int = 100, 
                          include_media: bool = False) -> Optional[List[Dict[str, Any]]]:
        """Get messages from the database"""
        try:
            params = {
                'room_id': room_id,
                'limit': limit
            }
            if include_media:
                params['include_media'] = 'true'
            
            # Build query string
            query_params = '&'.join([f"{k}={v}" for k, v in params.items()])
            url = f"{self.base_url}/messages?{query_params}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        print(f"❌ Get messages failed: {response.status} - {error_text}")
                        return None
                        
        except Exception as e:
            print(f"❌ Get messages error: {e}")
            return None
    
    async def upload_media(self, message_id: int, file_path: str) -> Optional[Dict[str, Any]]:
        """Upload media file to the database"""
        try:
            url = f"{self.base_url}/media/upload"
            file_path = Path(file_path)
            
            if not file_path.exists():
                print(f"❌ File does not exist: {file_path}")
                return None
            
            # Prepare headers for multipart upload (no Content-Type for multipart)
            upload_headers = {"Authorization": f"Bearer {self.api_key}"}
            
            async with aiohttp.ClientSession() as session:
                # Create form data
                data = aiohttp.FormData()
                data.add_field('message_id', str(message_id))
                
                # Read and add file
                async with aiofiles.open(file_path, 'rb') as f:
                    file_content = await f.read()
                    data.add_field(
                        'file', 
                        file_content,
                        filename=file_path.name,
                        content_type='application/octet-stream'
                    )
                
                async with session.post(
                    url,
                    headers=upload_headers,
                    data=data,
                    timeout=aiohttp.ClientTimeout(total=120)
                ) as response:
                    
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        print(f"❌ Upload media failed: {response.status} - {error_text}")
                        return None
                        
        except Exception as e:
            print(f"❌ Upload media error: {e}")
            return None
    
    async def get_database_stats(self) -> Optional[Dict[str, Any]]:
        """Get database statistics"""
        try:
            url = f"{self.base_url}/stats"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        print(f"❌ Get stats failed: {response.status} - {error_text}")
                        return None
                        
        except Exception as e:
            print(f"❌ Get stats error: {e}")
            return None
    
async def delete_message(self, message_id: int) -> bool:
        """Delete a message from the database by ID
        XXX Issue 1: implement delete_message
        """
        try:
            url = f"{self.base_url}/messages/{message_id}"
            print(f"🗑️ Deleting message ID: {message_id}")
            
            async with aiohttp.ClientSession() as session:
                async with session.delete(
                    url,
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        print(f"🗑️ Message {message_id} deleted successfully")
                        return True
                    else:
                        error_text = await response.text()
                        print(f"❌ Delete message failed: {response.status} - {error_text}")
                        return False
        except Exception as e:
            print(f"❌ Delete message error: {e}")
            return False

# Test function for the simplified client
async def test_client():
    """Test the API client"""
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    api_url = os.getenv("DATABASE_API_URL")
    api_key = os.getenv("DATABASE_API_KEY")
    
    if not api_url or not api_key:
        print("❌ Missing DATABASE_API_URL or DATABASE_API_KEY in .env")
        return
    
    print(f"🧪 Testing simplified API client...")
    print(f"📡 URL: {api_url}")
    print(f"🔑 Key: {api_key[:10]}...")
    
    client = ChatDatabaseClient(api_url, api_key)
    
    # Test health check
    print("\n🏥 Testing health check...")
    is_healthy = await client.health_check()
    print(f"Health status: {'✅ Healthy' if is_healthy else '❌ Unhealthy'}")
    
    # Test stats
    print("\n📊 Testing stats...")
    stats = await client.get_database_stats()
    if stats:
        print(f"✅ Stats retrieved: {stats}")
    else:
        print("❌ Failed to get stats")
    
    print("\n✅ Simplified API client test completed")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_client())

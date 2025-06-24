#!/usr/bin/env python3
"""
End-to-End Test for Media File Storage
Tests sending a text file to the Matrix room and verifying it gets stored in the database.
"""

import os
import asyncio
import tempfile
import aiohttp
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load environment
load_dotenv('.env')

DATABASE_API_URL = os.getenv('DATABASE_API_URL')
DATABASE_API_KEY = os.getenv('DATABASE_API_KEY')
ROOM_ID = os.getenv('ROOM_ID')

async def test_database_connection():
    """Test if we can connect to the database API"""
    print("🔍 Testing database connection...")
    
    try:
        url = f"{DATABASE_API_URL}/health"
        headers = {'Authorization': f'Bearer {DATABASE_API_KEY}'}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"✅ Database connection successful: {result}")
                    return True
                else:
                    print(f"❌ Database connection failed: {response.status}")
                    return False
                    
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return False

async def get_database_stats():
    """Get current database statistics"""
    print("📊 Getting database statistics...")
    
    try:
        url = f"{DATABASE_API_URL}/stats"
        headers = {'Authorization': f'Bearer {DATABASE_API_KEY}'}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"📊 Database stats:")
                    print(f"   Messages: {result.get('total_messages', 0)}")
                    print(f"   Media files: {result.get('total_media_files', 0)}")
                    print(f"   Size: {result.get('total_size_mb', 0):.2f} MB")
                    return result
                else:
                    print(f"❌ Stats request failed: {response.status}")
                    return None
                    
    except Exception as e:
        print(f"❌ Stats request error: {e}")
        return None

async def get_recent_messages(limit=10):
    """Get recent messages from the database"""
    print(f"📨 Getting {limit} recent messages...")
    
    try:
        url = f"{DATABASE_API_URL}/messages?room_id={ROOM_ID}&limit={limit}&include_media=true"
        headers = {'Authorization': f'Bearer {DATABASE_API_KEY}'}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    result = await response.json()
                    messages = result.get('messages', [])
                    print(f"📨 Found {len(messages)} recent messages:")
                    
                    for i, msg in enumerate(messages[:5]):  # Show first 5
                        print(f"   {i+1}. [{msg['message_type']}] {msg['sender']}: {msg['content'][:50]}...")
                        if msg.get('media_filename'):
                            print(f"      📎 Media: {msg['media_filename']}")
                    
                    return messages
                else:
                    print(f"❌ Messages request failed: {response.status}")
                    return []
                    
    except Exception as e:
        print(f"❌ Messages request error: {e}")
        return []

async def create_test_file():
    """Create a test text file"""
    print("📝 Creating test text file...")
    
    # Create a temporary text file
    test_content = f"""Test File for Bot Media Handling
Created: {datetime.now().isoformat()}
Room: {ROOM_ID}

This is a test file to verify that:
1. The bot can receive file messages
2. File messages get stored in the database
3. Media metadata is captured correctly

If you're seeing this in the database, the media handling is working! 🎉
"""
    
    # Write to temp file
    temp_dir = Path("./temp_media")
    temp_dir.mkdir(exist_ok=True)
    
    test_file = temp_dir / f"test_file_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    with open(test_file, 'w') as f:
        f.write(test_content)
    
    print(f"✅ Created test file: {test_file}")
    return test_file

async def check_for_new_media_messages(baseline_count):
    """Check if new media messages appeared after baseline"""
    print("🔍 Checking for new media messages...")
    
    messages = await get_recent_messages(20)
    media_messages = [msg for msg in messages if msg['message_type'] in ['file', 'image', 'video', 'audio', 'media']]
    
    print(f"📎 Found {len(media_messages)} total media messages")
    
    if len(media_messages) > baseline_count:
        print(f"✅ New media messages detected! (+{len(media_messages) - baseline_count})")
        
        # Show the newest media messages
        for msg in media_messages[:3]:
            print(f"   📎 {msg['message_type'].upper()}: {msg['content'][:60]}...")
            print(f"      From: {msg['sender']}")
            print(f"      Time: {msg['timestamp']}")
            if msg.get('media_filename'):
                print(f"      File: {msg['media_filename']}")
    else:
        print(f"⚠️ No new media messages detected")
    
    return len(media_messages)

async def main():
    """Run the end-to-end test"""
    print("🚀 Starting End-to-End Media Test")
    print("="*50)
    
    # Test 1: Database connection
    if not await test_database_connection():
        print("❌ Cannot connect to database - aborting test")
        return
    
    print()
    
    # Test 2: Get baseline stats
    baseline_stats = await get_database_stats()
    baseline_media_count = 0
    
    print()
    
    # Test 3: Get baseline message count
    messages = await get_recent_messages(20)
    media_messages = [msg for msg in messages if msg['message_type'] in ['file', 'image', 'video', 'audio', 'media']]
    baseline_media_count = len(media_messages)
    
    print()
    print("="*50)
    print("📋 TEST INSTRUCTIONS:")
    print("1. Start the bot if it's not running")
    print("2. Join the Matrix room with the bot")
    print("3. Send the test file created below to the room")
    print("4. Wait 10-30 seconds for processing")
    print("5. Re-run this script to check results")
    print("="*50)
    print()
    
    # Test 4: Create test file
    test_file = await create_test_file()
    
    print()
    print(f"📤 NEXT STEPS:")
    print(f"   1. Send this file to the Matrix room: {test_file}")
    print(f"   2. Wait for the bot to process it")
    print(f"   3. Run this script again to check if it was stored")
    
    print()
    print("🔍 To check results, run this script again or use bot commands:")
    print(f"   - Bot command: 'botname: db stats'")
    print(f"   - Bot command: 'botname: db health'")
    
    # Test 5: Check for changes (if this is a re-run)
    print()
    await check_for_new_media_messages(baseline_media_count)
    
    print()
    print("✅ Test setup complete!")

if __name__ == "__main__":
    asyncio.run(main())
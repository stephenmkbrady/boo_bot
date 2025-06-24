#!/usr/bin/env python3
"""
Quick test to verify database connection and check for recent media
"""

import asyncio
import os
from test_e2e_media import test_database_connection, get_database_stats, get_recent_messages

async def quick_check():
    print("🔧 Quick Database & Media Check")
    print("="*40)
    
    # Test database connection
    connected = await test_database_connection()
    if not connected:
        return
    
    # Get stats
    print()
    await get_database_stats()
    
    # Check recent messages
    print()
    messages = await get_recent_messages(10)
    
    # Count media messages
    media_messages = [msg for msg in messages if msg['message_type'] in ['file', 'image', 'video', 'audio', 'media']]
    text_messages = [msg for msg in messages if msg['message_type'] == 'text']
    
    print()
    print("📊 Message Summary:")
    print(f"   📝 Text messages: {len(text_messages)}")
    print(f"   📎 Media messages: {len(media_messages)}")
    print(f"   📊 Total recent: {len(messages)}")
    
    if media_messages:
        print("\n📎 Recent media messages:")
        for msg in media_messages[:3]:
            print(f"   - {msg['message_type'].upper()}: {msg['content'][:40]}...")
    
    print("\n✅ Quick check complete!")

if __name__ == "__main__":
    asyncio.run(quick_check())
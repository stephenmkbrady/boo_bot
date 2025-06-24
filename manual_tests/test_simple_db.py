#!/usr/bin/env python3
"""
Simple test to check if bot database integration is working
"""
import os
import sys
import asyncio

# Add current directory to path for imports
sys.path.append('/app')

from config import BotConfig
from plugins.database.plugin import ChatDatabaseClient

async def test_bot_db_integration():
    """Test the database integration like the bot would"""
    print("🔧 Testing Bot Database Integration")
    print("="*50)
    
    try:
        # Test 1: Load configuration like the bot does
        print("1. Loading bot configuration...")
        config = BotConfig()
        api_url = config.database_api_url
        api_key = config.database_api_key
        
        print(f"   Database URL: {api_url}")
        print(f"   API Key: {api_key[:10]}..." if api_key else "   API Key: Not set")
        
        if not api_url or not api_key:
            print("❌ Configuration incomplete!")
            return False
        
        # Test 2: Create database client like the plugin does
        print("\n2. Creating database client...")
        db_client = ChatDatabaseClient(api_url, api_key)
        print("✅ Database client created")
        
        # Test 3: Test connection
        print("\n3. Testing database connection...")
        is_healthy = await db_client.health_check()
        
        if is_healthy:
            print("✅ Database connection successful!")
        else:
            print("❌ Database health check failed")
            return False
        
        # Test 4: Get stats
        print("\n4. Getting database statistics...")
        stats = await db_client.get_database_stats()
        
        if stats:
            print(f"✅ Database stats retrieved:")
            print(f"   Messages: {stats.get('total_messages', 0)}")
            print(f"   Media files: {stats.get('total_media_files', 0)}")
            print(f"   Size: {stats.get('total_size_mb', 0):.2f} MB")
        else:
            print("❌ Could not retrieve database stats")
            return False
        
        # Test 5: Try to store a test message
        print("\n5. Testing message storage...")
        test_result = await db_client.store_message(
            room_id="!test:matrix.org",
            event_id=f"$test_{os.getpid()}",
            sender="@test:matrix.org", 
            message_type="text",
            content="Test message from bot integration test"
        )
        
        if test_result and 'id' in test_result:
            message_id = test_result['id']
            print(f"✅ Test message stored with ID: {message_id}")
            
            # Test 6: Try to delete the test message
            print("\n6. Cleaning up test message...")
            deleted = await db_client.delete_message(message_id)
            if deleted:
                print("✅ Test message cleaned up")
            else:
                print("⚠️ Could not clean up test message")
        else:
            print("❌ Failed to store test message")
            return False
        
        print("\n" + "="*50)
        print("✅ ALL TESTS PASSED - Database integration working!")
        print("✅ The bot should be able to:")
        print("   - Connect to the database")
        print("   - Store text messages automatically") 
        print("   - Store media messages automatically")
        print("   - Handle db health and db stats commands")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_bot_db_integration())
    if success:
        print("\n🎉 Database integration is ready!")
    else:
        print("\n💥 Database integration has issues!")
    sys.exit(0 if success else 1)
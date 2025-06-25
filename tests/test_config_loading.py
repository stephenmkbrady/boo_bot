#!/usr/bin/env python3
"""
Test to verify plugin configuration loading
"""
import sys
sys.path.append('/app')

from config import BotConfig

def test_config_loading():
    """Test that database config loads from plugins.yaml"""
    print("🔧 Testing Plugin Configuration Loading")
    print("="*50)
    
    try:
        # Load configuration
        config = BotConfig()
        
        # Check database plugin config
        db_config = config.get_plugin_config("database")
        
        print(f"Database plugin config: {db_config}")
        
        # URL from plugin config, API key from environment
        api_url = db_config.get("api_url")
        api_key = config.database_api_key  # From .env
        timeout = db_config.get("timeout")
        
        print(f"API URL (from plugins.yaml): {api_url}")
        print(f"API Key (from .env): {api_key[:10]}..." if api_key else "API Key: Not set")
        print(f"Timeout: {timeout}")
        
        if api_url and api_key:
            print("\n✅ Database configuration loaded successfully!")
            print("   - URL from plugins.yaml ✅")
            print("   - API key from .env ✅")
            assert True, "Configuration loaded successfully"
        else:
            print("\n❌ Database configuration incomplete!")
            if not api_url:
                print("   - Missing api_url in plugins.yaml")
            if not api_key:
                print("   - Missing DATABASE_API_KEY in .env")
            assert False, "Database configuration incomplete"
            
    except Exception as e:
        print(f"❌ Error loading configuration: {e}")
        import traceback
        traceback.print_exc()
        assert False, f"Error loading configuration: {e}"

if __name__ == "__main__":
    success = test_config_loading()
    print(f"\nResult: {'SUCCESS' if success else 'FAILED'}")
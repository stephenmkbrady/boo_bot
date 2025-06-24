#!/usr/bin/env python3
"""
Test for environment variable interpolation in plugins.yaml
"""
import os
import sys
import pytest
sys.path.append('/app' if os.path.exists('/app') else '.')

from config import BotConfig

def test_env_var_interpolation():
    """Test that environment variables are properly interpolated in YAML config"""
    # Set test environment variables
    test_url = "https://api.example.com:8000"
    test_key = "test_secret_key_12345"
    original_url = os.environ.get("DATABASE_API_URL")
    original_key = os.environ.get("DATABASE_API_KEY")
    
    try:
        os.environ["DATABASE_API_URL"] = test_url
        os.environ["DATABASE_API_KEY"] = test_key
        
        # Load config
        config = BotConfig()
        
        # Check if database plugin config loaded correctly
        db_config = config.get_plugin_config("database")
        api_url = db_config.get("api_url")
        api_key = db_config.get("api_key")
        
        # Verify interpolation worked
        assert api_url == test_url, f"Expected {test_url}, got {api_url}"
        assert api_key == test_key, f"Expected {test_key}, got {api_key}"
        
    finally:
        # Restore original environment variables
        if original_url is not None:
            os.environ["DATABASE_API_URL"] = original_url
        elif "DATABASE_API_URL" in os.environ:
            del os.environ["DATABASE_API_URL"]
            
        if original_key is not None:
            os.environ["DATABASE_API_KEY"] = original_key
        elif "DATABASE_API_KEY" in os.environ:
            del os.environ["DATABASE_API_KEY"]

def test_env_var_fallback():
    """Test that missing environment variables don't break config loading"""
    # Remove the environment variable if it exists
    original_value = os.environ.get("NONEXISTENT_VAR")
    
    try:
        if "NONEXISTENT_VAR" in os.environ:
            del os.environ["NONEXISTENT_VAR"]
        
        # Create a temporary config content with missing env var
        from config import BotConfig
        config_instance = BotConfig()
        
        # Test substitution with missing variable
        content = "api_url: ${NONEXISTENT_VAR}"
        result = config_instance._substitute_env_vars(content)
        
        # Should return original pattern if env var doesn't exist
        assert result == "api_url: ${NONEXISTENT_VAR}"
        
    finally:
        if original_value is not None:
            os.environ["NONEXISTENT_VAR"] = original_value

def test_multiple_env_vars():
    """Test multiple environment variable substitutions in one config"""
    # Set multiple test environment variables
    test_vars = {
        "TEST_URL": "https://test.com",
        "TEST_TIMEOUT": "60"
    }
    
    original_values = {}
    for var in test_vars:
        original_values[var] = os.environ.get(var)
    
    try:
        # Set test values
        for var, value in test_vars.items():
            os.environ[var] = value
        
        # Test substitution
        from config import BotConfig
        config_instance = BotConfig()
        
        content = """
api_url: ${TEST_URL}
timeout: ${TEST_TIMEOUT}
other: normal_value
"""
        result = config_instance._substitute_env_vars(content)
        
        expected = """
api_url: https://test.com
timeout: 60
other: normal_value
"""
        assert result == expected
        
    finally:
        # Restore original values
        for var, original_value in original_values.items():
            if original_value is not None:
                os.environ[var] = original_value
            elif var in os.environ:
                del os.environ[var]
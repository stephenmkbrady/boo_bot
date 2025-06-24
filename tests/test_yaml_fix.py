#!/usr/bin/env python3
import os
import yaml
import re
import pytest

def test_yaml_generation():
    """Test that the YAML generation works correctly"""
    
    # Test content
    content = """admin_users: ${ADMIN_USERS}
admin_rooms: ${ADMIN_ROOMS}"""
    
    # Set environment variables
    os.environ["ADMIN_USERS"] = "@admin:matrix.org,@owner:matrix.org"
    os.environ["ADMIN_ROOMS"] = "!admin:matrix.org"
    
    def replace_var(match):
        var_name = match.group(1)
        env_value = os.getenv(var_name)
        if env_value is None:
            return match.group(0)
        
        if var_name in ['ADMIN_USERS', 'ADMIN_ROOMS']:
            items = [item.strip() for item in env_value.split(',') if item.strip()]
            return '[' + ', '.join(f'"{item}"' for item in items) + ']'
        
        return env_value
    
    pattern = r'\$\{([A-Z_][A-Z0-9_]*)\}'
    result = re.sub(pattern, replace_var, content)
    
    # Test YAML parsing
    data = yaml.safe_load(result)
    
    # Verify the results
    assert isinstance(data['admin_users'], list)
    assert data['admin_users'] == ["@admin:matrix.org", "@owner:matrix.org"]
    assert isinstance(data['admin_rooms'], list)
    assert data['admin_rooms'] == ["!admin:matrix.org"]

def test_yaml_single_item():
    """Test YAML generation with single items"""
    content = "admin_users: ${ADMIN_USERS}"
    
    # Test single item
    os.environ["ADMIN_USERS"] = "@singleadmin:matrix.org"
    
    def replace_var(match):
        var_name = match.group(1)
        env_value = os.getenv(var_name)
        if env_value is None:
            return match.group(0)
        
        if var_name in ['ADMIN_USERS', 'ADMIN_ROOMS']:
            items = [item.strip() for item in env_value.split(',') if item.strip()]
            return '[' + ', '.join(f'"{item}"' for item in items) + ']'
        
        return env_value
    
    pattern = r'\$\{([A-Z_][A-Z0-9_]*)\}'
    result = re.sub(pattern, replace_var, content)
    
    data = yaml.safe_load(result)
    assert data['admin_users'] == ["@singleadmin:matrix.org"]

def test_yaml_empty_env_var():
    """Test YAML generation with empty environment variable"""
    content = "admin_users: ${ADMIN_USERS}"
    
    # Test empty value
    os.environ["ADMIN_USERS"] = ""
    
    def replace_var(match):
        var_name = match.group(1)
        env_value = os.getenv(var_name)
        if env_value is None:
            return match.group(0)
        
        if var_name in ['ADMIN_USERS', 'ADMIN_ROOMS']:
            items = [item.strip() for item in env_value.split(',') if item.strip()]
            return '[' + ', '.join(f'"{item}"' for item in items) + ']'
        
        return env_value
    
    pattern = r'\$\{([A-Z_][A-Z0-9_]*)\}'
    result = re.sub(pattern, replace_var, content)
    
    data = yaml.safe_load(result)
    assert data['admin_users'] == []
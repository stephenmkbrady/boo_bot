#!/usr/bin/env python3
"""
Tests for dynamic configuration management system
"""
import os
import sys
import pytest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.append('/app' if os.path.exists('/app') else '.')

from config import BotConfig
from config_manager import ConfigManager
from plugins.core.plugin import CorePlugin


class TestConfigManager:
    """Test the ConfigManager class"""
    
    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = Path(self.temp_dir) / "plugins.yaml"
        self.config_manager = ConfigManager()
        self.config_manager.config_file = self.config_file
        self.config_manager.backup_file = self.config_file.with_suffix('.yaml.backup')
        
        # Create test config file
        test_config = {
            'ai': {
                'enabled': True,
                'config': {
                    'model': 'test-model',
                    'temperature': 0.3,
                    'max_tokens': 500
                }
            },
            'youtube': {
                'enabled': True,
                'config': {
                    'max_cached_per_room': 5,
                    'chunk_size': 8000
                }
            }
        }
        
        with open(self.config_file, 'w') as f:
            yaml.dump(test_config, f)
    
    def test_validate_plugin_setting_valid(self):
        """Test validation of valid plugin settings"""
        # Valid AI settings
        valid, error, value = self.config_manager.validate_plugin_setting("ai", "model", "gpt-4")
        assert valid == True
        assert value == "gpt-4"
        
        valid, error, value = self.config_manager.validate_plugin_setting("ai", "temperature", "0.7")
        assert valid == True
        assert value == 0.7
        
        valid, error, value = self.config_manager.validate_plugin_setting("ai", "max_tokens", "1000")
        assert valid == True
        assert value == 1000
        
        # Valid YouTube settings
        valid, error, value = self.config_manager.validate_plugin_setting("youtube", "max_cached_per_room", "10")
        assert valid == True
        assert value == 10
    
    def test_validate_plugin_setting_invalid(self):
        """Test validation of invalid plugin settings"""
        # Invalid plugin name
        valid, error, value = self.config_manager.validate_plugin_setting("bad-plugin", "setting", "value")
        assert valid == False
        assert "Invalid plugin name" in error
        
        # Invalid setting name
        valid, error, value = self.config_manager.validate_plugin_setting("ai", "bad-setting!", "value")
        assert valid == False
        assert "Invalid setting name" in error
        
        # Invalid AI temperature
        valid, error, value = self.config_manager.validate_plugin_setting("ai", "temperature", "5.0")
        assert valid == False
        assert "temperature must be between 0.0 and 2.0" in error
        
        # Security: database API settings
        valid, error, value = self.config_manager.validate_plugin_setting("database", "api_key", "new-key")
        assert valid == False
        assert "cannot be changed via chat commands for security" in error
    
    def test_parse_config_value(self):
        """Test parsing of different value types"""
        # Boolean values
        assert self.config_manager._parse_config_value("true") == True
        assert self.config_manager._parse_config_value("false") == False
        assert self.config_manager._parse_config_value("yes") == True
        assert self.config_manager._parse_config_value("no") == False
        
        # Numeric values
        assert self.config_manager._parse_config_value("42") == 42
        assert self.config_manager._parse_config_value("3.14") == 3.14
        
        # String values
        assert self.config_manager._parse_config_value('"hello world"') == "hello world"
        assert self.config_manager._parse_config_value("'quoted'") == "quoted"
        assert self.config_manager._parse_config_value("plain") == "plain"
    
    def test_get_plugin_setting(self):
        """Test getting plugin settings"""
        # Mock BotConfig to return our test config
        with patch('config_manager.BotConfig') as mock_config:
            mock_instance = mock_config.return_value
            mock_instance.get_plugin_config.return_value = {
                'model': 'test-model',
                'temperature': 0.3,
                'max_tokens': 500
            }
            
            success, error, value = self.config_manager.get_plugin_setting("ai", "model")
            assert success == True
            assert value == "test-model"
            
            success, error, value = self.config_manager.get_plugin_setting("ai", "temperature")
            assert success == True
            assert value == 0.3
    
    def test_set_plugin_setting(self):
        """Test setting plugin settings"""
        # Set a new value
        success, error = self.config_manager.set_plugin_setting("ai", "temperature", 0.8)
        assert success == True
        
        # Verify it was written to file
        with open(self.config_file, 'r') as f:
            data = yaml.safe_load(f)
        
        assert data['ai']['config']['temperature'] == 0.8
        
        # Test creating new plugin
        success, error = self.config_manager.set_plugin_setting("newplugin", "setting1", "value1")
        assert success == True
        
        with open(self.config_file, 'r') as f:
            data = yaml.safe_load(f)
        
        assert 'newplugin' in data
        assert data['newplugin']['config']['setting1'] == "value1"


class TestConfigAuthorization:
    """Test configuration authorization system"""
    
    def test_admin_authorization(self):
        """Test admin user and room authorization"""
        # Mock environment variables
        with patch.dict(os.environ, {
            'ADMIN_USERS': '@admin1:matrix.org,@admin2:matrix.org',
            'ADMIN_ROOMS': '!room1:matrix.org,!room2:matrix.org'
        }):
            config = BotConfig()
            
            # Test admin users
            assert config.is_admin_user('@admin1:matrix.org') == True
            assert config.is_admin_user('@admin2:matrix.org') == True
            assert config.is_admin_user('@user:matrix.org') == False
            
            # Test admin rooms
            assert config.is_admin_room('!room1:matrix.org') == True
            assert config.is_admin_room('!room2:matrix.org') == True
            assert config.is_admin_room('!room3:matrix.org') == False
            
            # Test full authorization
            assert config.is_authorized_for_config('@admin1:matrix.org', '!room1:matrix.org') == True
            assert config.is_authorized_for_config('@admin1:matrix.org', '!room3:matrix.org') == False
            assert config.is_authorized_for_config('@user:matrix.org', '!room1:matrix.org') == False


@pytest.mark.asyncio
class TestCorePluginConfig:
    """Test the CorePlugin config command implementation"""
    
    def setup_method(self):
        """Setup test environment"""
        self.plugin = CorePlugin()
        self.mock_bot = MagicMock()
        self.mock_bot.plugin_manager = MagicMock()
    
    async def test_config_authorization_required(self):
        """Test that config commands require authorization"""
        await self.plugin.initialize(self.mock_bot)
        
        with patch('plugins.core.plugin.BotConfig') as mock_config:
            mock_instance = mock_config.return_value
            mock_instance.is_authorized_for_config.return_value = False
            
            result = await self.plugin._handle_config("list ai", "!room:matrix.org", "@user:matrix.org", self.mock_bot)
            assert "not authorized" in result
    
    async def test_config_help(self):
        """Test config help command"""
        await self.plugin.initialize(self.mock_bot)
        
        with patch('plugins.core.plugin.BotConfig') as mock_config:
            mock_instance = mock_config.return_value
            mock_instance.is_authorized_for_config.return_value = True
            
            result = await self.plugin._handle_config("", "!room:matrix.org", "@admin:matrix.org", self.mock_bot)
            assert "Configuration Commands" in result
            assert "config list" in result
            assert "config set" in result
    
    async def test_config_list_command(self):
        """Test config list command"""
        await self.plugin.initialize(self.mock_bot)
        
        with patch('plugins.core.plugin.BotConfig') as mock_config:
            mock_instance = mock_config.return_value
            mock_instance.is_authorized_for_config.return_value = True
            
            with patch.object(self.plugin.config_manager, 'list_plugin_settings') as mock_list:
                mock_list.return_value = (True, "", {"model": "test-model", "temperature": 0.3})
                
                result = await self.plugin._handle_config("list ai", "!room:matrix.org", "@admin:matrix.org", self.mock_bot)
                assert "Ai Plugin Settings" in result
                assert "model" in result
                assert "temperature" in result
    
    async def test_config_get_command(self):
        """Test config get command"""
        await self.plugin.initialize(self.mock_bot)
        
        with patch('plugins.core.plugin.BotConfig') as mock_config:
            mock_instance = mock_config.return_value
            mock_instance.is_authorized_for_config.return_value = True
            
            with patch.object(self.plugin.config_manager, 'get_plugin_setting') as mock_get:
                mock_get.return_value = (True, "", "test-model")
                
                result = await self.plugin._handle_config("get ai model", "!room:matrix.org", "@admin:matrix.org", self.mock_bot)
                assert "ai.model" in result
                assert "test-model" in result
    
    async def test_config_set_command(self):
        """Test config set command"""
        await self.plugin.initialize(self.mock_bot)
        
        # Make the async method return a coroutine
        async def mock_reload():
            return True
        self.mock_bot.plugin_manager._handle_config_change = MagicMock(side_effect=mock_reload)
        
        with patch('plugins.core.plugin.BotConfig') as mock_config:
            mock_instance = mock_config.return_value
            mock_instance.is_authorized_for_config.return_value = True
            
            with patch.object(self.plugin.config_manager, 'validate_plugin_setting') as mock_validate:
                mock_validate.return_value = (True, "", "new-model")
                
                with patch.object(self.plugin.config_manager, 'set_plugin_setting') as mock_set:
                    mock_set.return_value = (True, "")
                    
                    result = await self.plugin._handle_config("set ai model new-model", "!room:matrix.org", "@admin:matrix.org", self.mock_bot)
                    assert "✅ Set" in result
                    assert "ai.model" in result
                    assert "new-model" in result
                    
                    # Verify hot reload was triggered
                    self.mock_bot.plugin_manager._handle_config_change.assert_called_once()
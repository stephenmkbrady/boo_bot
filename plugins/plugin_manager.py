import os
import sys
import importlib
import importlib.util
from pathlib import Path
from typing import Dict, List, Optional, Set
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import asyncio
import threading
import time
from plugins.plugin_interface import BotPlugin

class PluginFileHandler(FileSystemEventHandler):
    """File system event handler for plugin hot reloading"""
    
    def __init__(self, plugin_manager):
        super().__init__()
        self.plugin_manager = plugin_manager
        self.last_modified = {}
        self.debounce_time = 1.0  # 1 second debounce to avoid multiple rapid reloads
        
    def on_modified(self, event):
        if event.is_directory:
            return
        
        if not event.src_path.endswith('plugin.py'):
            return
        
        # Debounce rapid file changes
        current_time = time.time()
        if event.src_path in self.last_modified:
            if current_time - self.last_modified[event.src_path] < self.debounce_time:
                return
        
        self.last_modified[event.src_path] = current_time
        
        # Schedule reload in the main thread
        plugin_file = Path(event.src_path)
        asyncio.run_coroutine_threadsafe(
            self.plugin_manager._handle_file_change(plugin_file),
            self.plugin_manager.loop
        )
    
    def on_deleted(self, event):
        if event.is_directory:
            return
        
        if not event.src_path.endswith('plugin.py'):
            return
            
        plugin_file = Path(event.src_path)
        asyncio.run_coroutine_threadsafe(
            self.plugin_manager._handle_file_deletion(plugin_file),
            self.plugin_manager.loop
        )

class PluginManager:
    def __init__(self, plugins_dir: str = "plugins"):
        self.plugins: Dict[str, BotPlugin] = {}
        self.plugins_dir = Path(plugins_dir)
        self.failed_plugins: Dict[str, str] = {}
        self.bot_instance = None
        self.loop = None
        self.file_observer = None
        self.file_handler = None
        self.module_cache: Dict[str, any] = {}
        
        # Ensure plugins directory exists
        self.plugins_dir.mkdir(exist_ok=True)
        
        print(f"🔌 Plugin manager initialized for directory: {self.plugins_dir}")
        
    async def start_hot_reloading(self):
        """Start file system monitoring for hot reloading"""
        try:
            self.loop = asyncio.get_event_loop()
            self.file_handler = PluginFileHandler(self)
            self.file_observer = Observer()
            self.file_observer.schedule(
                self.file_handler, 
                str(self.plugins_dir), 
                recursive=True
            )
            self.file_observer.start()
            print("🔥 Hot reloading enabled - watching for plugin changes...")
        except Exception as e:
            print(f"⚠️ Could not start hot reloading: {e}")
    
    async def stop_hot_reloading(self):
        """Stop file system monitoring"""
        if self.file_observer:
            self.file_observer.stop()
            self.file_observer.join()
            print("🔥 Hot reloading stopped")
    
    async def _handle_file_change(self, plugin_file: Path):
        """Handle plugin file modification"""
        # Extract plugin name from the parent directory
        plugin_name = plugin_file.parent.name
        print(f"🔥 Plugin file changed: {plugin_name}")
        
        if plugin_name in self.plugins:
            # Reload existing plugin
            await self.reload_plugin(plugin_name)
        else:
            # Load new plugin
            await self.load_plugin_from_file(plugin_file, self.bot_instance, plugin_name)
    
    async def _handle_file_deletion(self, plugin_file: Path):
        """Handle plugin file deletion"""
        plugin_name = plugin_file.parent.name
        print(f"🗑️ Plugin file deleted: {plugin_name}")
        
        if plugin_name in self.plugins:
            await self.unload_plugin(plugin_name)

    async def discover_and_load_plugins(self, bot_instance) -> Dict[str, bool]:
        """Automatically discover and load all plugins from plugins directory"""
        self.bot_instance = bot_instance
        results = {}
        
        # Look for plugin.py files in plugin subfolders
        for plugin_dir in self.plugins_dir.iterdir():
            if plugin_dir.is_dir() and not plugin_dir.name.startswith('__'):
                plugin_file = plugin_dir / "plugin.py"
                if plugin_file.exists():
                    plugin_name = plugin_dir.name
                    success = await self.load_plugin_from_file(plugin_file, bot_instance, plugin_name)
                    results[plugin_name] = success
            
        print(f"✅ Plugin discovery complete: {len(self.plugins)} loaded, {len(self.failed_plugins)} failed")
        
        # Start hot reloading after initial load
        await self.start_hot_reloading()
        
        return results
    
    async def load_plugin_from_file(self, plugin_file: Path, bot_instance, plugin_name: str = None) -> bool:
        """Load a specific plugin from file"""
        if plugin_name is None:
            plugin_name = plugin_file.stem
        
        try:
            # Remove from cache if exists (for hot reloading)
            module_name = f"plugins.{plugin_name}.plugin"
            if module_name in sys.modules:
                del sys.modules[module_name]
            
            # Also remove the parent module if exists
            parent_module_name = f"plugins.{plugin_name}"
            if parent_module_name in sys.modules:
                del sys.modules[parent_module_name]
            
            # Dynamically import the plugin module
            spec = importlib.util.spec_from_file_location(module_name, plugin_file)
            if not spec or not spec.loader:
                raise ImportError(f"Could not load spec for {plugin_file}")
                
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Find plugin class - look for classes that inherit from BotPlugin
            plugin_class = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and 
                    issubclass(attr, BotPlugin) and 
                    attr != BotPlugin):
                    plugin_class = attr
                    break
            
            if not plugin_class:
                raise ImportError(f"No BotPlugin subclass found in {plugin_file}")
            
            # Create plugin instance
            plugin = plugin_class()
            
            # Initialize plugin
            if await plugin.initialize(bot_instance):
                # Cleanup old plugin if reloading
                if plugin.name in self.plugins:
                    old_plugin = self.plugins[plugin.name]
                    await old_plugin.cleanup()
                
                self.plugins[plugin.name] = plugin
                self.failed_plugins.pop(plugin_name, None)  # Clear any previous failures
                print(f"✅ Loaded plugin: {plugin.name} v{plugin.version}")
                return True
            else:
                raise Exception("Plugin initialization failed")
                
        except Exception as e:
            error_msg = f"Failed to load plugin {plugin_name}: {e}"
            print(f"❌ {error_msg}")
            self.failed_plugins[plugin_name] = str(e)
            return False
    
    async def reload_plugin(self, plugin_name: str) -> bool:
        """Reload a specific plugin"""
        print(f"🔄 Reloading plugin: {plugin_name}")
        
        # Find the plugin file in subfolder
        plugin_file = self.plugins_dir / plugin_name / "plugin.py"
        if not plugin_file.exists():
            print(f"❌ Plugin file not found: {plugin_file}")
            return False
        
        # Unload current plugin
        if plugin_name in self.plugins:
            await self.unload_plugin(plugin_name, announce=False)
        
        # Load new version
        success = await self.load_plugin_from_file(plugin_file, self.bot_instance)
        
        if success:
            print(f"✅ Plugin {plugin_name} reloaded successfully")
        else:
            print(f"❌ Failed to reload plugin {plugin_name}")
        
        return success
    
    async def unload_plugin(self, plugin_name: str, announce: bool = True) -> bool:
        """Unload a specific plugin"""
        if plugin_name not in self.plugins:
            return False
        
        try:
            # Cleanup plugin
            plugin = self.plugins[plugin_name]
            await plugin.cleanup()
            
            # Remove from active plugins
            del self.plugins[plugin_name]
            
            if announce:
                print(f"🗑️ Unloaded plugin: {plugin_name}")
            
            return True
        except Exception as e:
            print(f"❌ Error unloading plugin {plugin_name}: {e}")
            return False
    
    def enable_plugin(self, plugin_name: str) -> bool:
        """Enable a specific plugin"""
        if plugin_name in self.plugins:
            self.plugins[plugin_name].enabled = True
            print(f"✅ Enabled plugin: {plugin_name}")
            return True
        return False
    
    def disable_plugin(self, plugin_name: str) -> bool:
        """Disable a specific plugin"""
        if plugin_name in self.plugins:
            self.plugins[plugin_name].enabled = False
            print(f"⏸️ Disabled plugin: {plugin_name}")
            return True
        return False

    async def handle_command(self, command: str, args: str, room_id: str, user_id: str, bot_instance) -> Optional[str]:
        """Try to handle command with available plugins"""
        for plugin in self.plugins.values():
            if plugin.enabled and plugin.can_handle(command):
                try:
                    result = await plugin.handle_command(command, args, room_id, user_id, bot_instance)
                    if result is not None:
                        return result
                except Exception as e:
                    print(f"❌ Plugin {plugin.name} error handling {command}: {e}")
                    # Continue to next plugin instead of crashing
                    continue
        return None
    
    def get_all_commands(self) -> Dict[str, str]:
        """Get all available commands mapped to plugin names"""
        commands = {}
        for plugin in self.plugins.values():
            if plugin.enabled:
                for cmd in plugin.get_commands():
                    commands[cmd] = plugin.name
        return commands
    
    def get_plugin_status(self) -> Dict[str, any]:
        """Get status of all plugins"""
        return {
            "loaded": {name: plugin.get_info() for name, plugin in self.plugins.items()},
            "failed": self.failed_plugins,
            "total_loaded": len(self.plugins),
            "total_failed": len(self.failed_plugins),
            "hot_reloading": self.file_observer is not None and self.file_observer.is_alive()
        }
    
    async def cleanup(self):
        """Cleanup plugin manager"""
        await self.stop_hot_reloading()
        
        # Cleanup all plugins
        for plugin in list(self.plugins.values()):
            await plugin.cleanup()
        
        self.plugins.clear()
        print("🔌 Plugin manager cleanup complete")
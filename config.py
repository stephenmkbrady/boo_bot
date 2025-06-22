import os
from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class FeatureConfig:
    enabled: bool
    config: Dict[str, Any]

class BotConfig:
    def __init__(self):
        # Matrix config
        self.homeserver = os.getenv("HOMESERVER", "https://matrix.org")
        self.user_id = os.getenv("USER_ID")
        self.password = os.getenv("PASSWORD")
        self.room_id = os.getenv("ROOM_ID")
        
        # Feature flags
        self.features = {
            "youtube": FeatureConfig(
                enabled=bool(os.getenv("OPENROUTER_API_KEY")),
                config={"max_cached_per_room": 5}
            ),
            "ai": FeatureConfig(
                enabled=bool(os.getenv("OPENROUTER_API_KEY")),
                config={"model": "meta-llama/llama-3.2-3b-instruct:free"}
            ),
            "media": FeatureConfig(
                enabled=bool(os.getenv("DATABASE_API_KEY")),
                config={"temp_dir": "./temp_media"}
            ),
            "database": FeatureConfig(
                enabled=bool(os.getenv("DATABASE_API_KEY")),
                config={}
            )
        }
        
        # API keys
        self.openrouter_key = os.getenv("OPENROUTER_API_KEY")
        self.database_api_key = os.getenv("DATABASE_API_KEY")
        self.database_api_url = os.getenv("DATABASE_API_URL")
    
    def is_feature_enabled(self, feature_name: str) -> bool:
        return self.features.get(feature_name, FeatureConfig(False, {})).enabled
    
    def get_feature_config(self, feature_name: str) -> Dict[str, Any]:
        return self.features.get(feature_name, FeatureConfig(False, {})).config
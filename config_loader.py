import yaml
import os

class Config:
    _instance = None
    _config = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        config_path = "config.yaml"
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    self._config = yaml.safe_load(f) or {}
            except yaml.YAMLError as e:
                print(f"CRITICAL: Failed to parse config.yaml: {e}")
                self._config = {}
        else:
            print(f"WARNING: config.yaml not found at {config_path}. Using empty defaults.")
            self._config = {}

    def get(self, key_path, default=None):
        """
        Retrieves a value from the config using a dot-separated path.
        Example: config.get("models.junior_analyst.name")
        """
        keys = key_path.split(".")
        value = self._config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value

# Singleton instance
config = Config()

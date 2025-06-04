import yaml
import os

def load_config(config_path="configs/config.yaml"):
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


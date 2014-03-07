#
"""
Handle configuration files
"""
import yaml

def get_config(filename):
    """Get dict from YAML configution file"""
    with open(filename) as f:
        return yaml.load(f)


# -*- coding: utf-8 -*-
"""
nsl.common.config

Handle NSL configuration files (YAML)

Functions
---------
get_config(filename) : read in a one-doc YAML file to dict
"""
import yaml

def get_config(filename):
    """Get dict from YAML configution file"""
    with open(filename) as f:
        return yaml.load(f)

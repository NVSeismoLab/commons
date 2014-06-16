# -*- coding: utf-8 -*-
"""
nsl.common.config

Handle common NSL configuration files

Supported formats
-----------------
    JSON : natively supported
    YAML : need PyYAML
    pf   : need antelope


Functions
---------
get_yaml : yaml from file handle or string content
get_json : json from file handle or string content


Main
----
get_config(filename, kind=None) : read in a file to dict
    filename : str of filename
    kind : specify type, uses extension if None

"""

def get_yaml(fh):
    """YAML to object with input type detection"""
    import yaml
    if isinstance(fh, file):
        return yaml.load(fh)
    elif isinstance(fh, str):
        return yaml.loads(fh)


def get_json(fh):
    """JSON to object with input type detection"""
    import json
    if isinstance(fh, file):
        return json.load(fh)
    elif isinstance(fh, str):
        return json.loads(fh)


class Configuration(dict):
    """
    Preliminary dict class to hold config info

    If file is not top-level mapping object, the content
    is stored as the attribute '__content__'

    """
    __content__ = None

    @property
    def settings(self):
        return self.keys()

    @classmethod
    def from_file(cls, filename, kind=None):
        """
        Configuration from a string filename
        """
        if filename.endswith('.yml') or kind=='YAML':
            func = get_yaml
        elif filename.endswith('.json') or kind=='JSON':
            func = get_json
        elif filename.endswith('.pf') or kind=='PF':
            from nsl.antelope.pf import get_pf
            func = get_pf
        else:
            raise NotImplementedError("No support for format: {0} type={1}".format(filename, kind))

        with open(filename) as f:
            c = func(f)
            try:
                config =  cls(**c)
            except:
                config = cls()
                config.__content__ = c
            finally:
                return config

# Function, just link to constructor for now
get_config = Configuration.from_file


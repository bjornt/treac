import os
import sys
import subprocess

import yaml


_CONFIG = 'configuration'

DEFAULT_PORT = 8080
DEFAULT_BIND_ADDRESS = "0.0.0.0"


def set_config(config_yaml):
    config_file = get_config_file()
    with open(config_file, 'w') as f:
        yaml.dump(config_yaml, stream=f, default_flow_style=False)


def get_config_file():
    return os.path.join(os.environ['SNAP_DATA'], _CONFIG)


def get_config():
    config_file = get_config_file()
    try:
        with open(config_file) as f:
            return yaml.load(f)
    except FileNotFoundError:
        return _get_default_config()


def _get_default_config():
    return {
        'config': {
            os.environ["SNAP_NAME"]: {
                'port': DEFAULT_PORT,
                'bind-address': DEFAULT_BIND_ADDRESS}}}

def log(message):
    with open(os.path.join(os.environ['SNAP_DATA'], "log"), "a") as f:
        f.write(message)
        f.write("\n")

def treac_snap_config():
    new_config = yaml.load(sys.stdin)
    config = get_config()
    if new_config:
        config["config"][os.environ["SNAP_NAME"]].update(
            new_config["config"][os.environ["SNAP_NAME"]])
        set_config(config)

    yaml.dump(get_config(), stream=sys.stdout,
              default_flow_style=False)


def treacd_wrapper():
    new_config = yaml.load(sys.stdin)
    os.environ["HOME"] = os.environ["SNAP_DATA"]
    python_path = os.path.join(
        os.environ['SNAP'], 'usr', 'bin', 'python3')
    treacd_path = os.path.join(
        os.environ['SNAP'], 'usr', 'bin', 'treac')
    config = get_config()["config"][os.environ['SNAP_NAME']]
    subprocess.call(
        [python_path, treacd_path, "--port", str(config["port"]),
         config['bind-address']])

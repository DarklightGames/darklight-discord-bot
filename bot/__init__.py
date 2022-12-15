from .config import Config

__version__ = '0.1.0'

config: Config = Config.load_from('./config.yaml')
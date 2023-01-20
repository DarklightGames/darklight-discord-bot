from __future__ import annotations

import yaml
import sys
import logging
from dataclasses import dataclass
from typing import Optional, Self
from dacite.core import from_dict


@dataclass
class Server:
    """
    Server info used for querries.
    
    Attributes
    ----------
        name : Server name (unused).
        address : IP address of the game server.
        query_port : Port for the query protocol.
    """

    name: str
    address: str
    query_port: int


@dataclass
class EventSettings:
    """
    Settings for the event roster extension.

    Attributes
    ----------
        axis_role : `ID` of the `Axis` team role in the main guild.
        allied_role : `ID` of the `Allies` team role in the main guild.
        sl_role : `ID` of the squad leader role in the main guild.
    """

    axis_role: int
    allied_role: int
    sl_role: int


@dataclass
class ServerBrowserSettings:
    """
    Settings for the server browser extension.

    Attributes
    ----------
        servers : `List` of game servers to query.
        channel : `ID` of the dedicated channel in the main guild where server info will be posted and updated.
        query_inteval : Interval for querying `servers` and updating info in the set `channel` (in seconds).
    """

    servers: list[Server]
    channel: int
    query_interval: float


@dataclass
class Config:
    """
    Main settings class for the bot.

    Attributes
    ----------
        guild : Main guild `ID`.
        server_browser : Settings object for the server browser extension.
        event_roster : Settings object for the event roster extension.
    """
    
    guild: int
    server_browser: ServerBrowserSettings
    event_roster: EventSettings

    @staticmethod
    def load_from(path: str) -> Config:
        """Loads config from a `yaml` file."""
        config: dict = {}

        try:
            with open(path, 'r') as config_file:
                config = yaml.safe_load(config_file)
        except yaml.YAMLError:
            logging.error('Failed to parse the configuration file')
            sys.exit(1)
        except FileNotFoundError:
            logging.error('Configuration file not found')
            sys.exit(1)

        return from_dict(data_class=Config, data=config)

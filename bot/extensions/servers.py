from typing import Sequence, Iterator

import logging
import asyncio
import time

import hikari
import lightbulb
from lightbulb.ext import tasks

import bot as darklight_bot
from bot.config import ServerBrowserSettings
from bot.utils import unreal_query


plugin = lightbulb.Plugin('ServerBrowser')


class Server():
    def __init__(self, addr: tuple[str, int], default_name: str) -> None:
        self.name = default_name
        self.addr = addr
        self.info: unreal_query.ServerInfo | None = None
        self.players: int = 0
        self.max_players: int = 0
        self.map: str = ''
        self.failed_updates: int = 0
        self.is_online: bool = False

    async def update(self) -> None:
        self.info = await unreal_query.query(self.addr)

        if self.info:
            self.name = self.info.name
            self.map = self.info.map
            self.players = self.info.players
            self.max_players = self.info.max_players
            self.failed_updates = 0
            self.is_online = True
        else:
            self.failed_updates = min(self.failed_updates + 1, 3)

            if self.failed_updates >= 3:
                self.is_online = False
                self.players = 0
            else:
                self.map = 'Refreshing...'


class ServerCollection():
    def __init__(self, servers: Sequence[Server]):
        self.servers = servers

    def __iter__(self) -> Iterator[Server]:
        for s in self.servers:
            yield s

    def __bool__(self) -> bool:
        return any(True for _ in self.servers)

    def get_total_players(self) -> int:
        return sum([ s.players for s in self.servers])

    async def update(self) -> None:
        coros = [ s.update() for s in self.servers ]
        await asyncio.gather(*coros)


class BulletinBoard():
    """A class for publishing embeds into multiple persistent messages and keeping them updated"""

    def __init__(self) -> None:
        self.embeds: list[hikari.Embed] = []

    def add_embed(self, embed: hikari.Embed) -> None:
        """Adds an embed to be published on the board"""
        self.embeds.append(embed)

    async def push_to_channel(self, channel: hikari.TextableChannel) -> None:
        """
        Updates bot's latest messages with current embeds. New messages are created if necessary.

        Parameters
        ----------
        channel : Textable channel to update
        """

        me: hikari.OwnUser | None = plugin.bot.get_me()

        if not me:
            logging.error('Failed to fetch the bot user.')
            return

        try:
            messages: list[hikari.Message] = [ x
                                               for x in await plugin.bot.rest.fetch_messages(channel)
                                               if x.author.id == me.id ]

            messages_reversed: list[hikari.Message] = [*reversed(messages[:len(self.embeds)])]

            for idx, embed in enumerate(self.embeds):
                if idx >= len(messages_reversed):
                    await channel.send(content='', embed=embed)
                else:
                    # WARNING: This will hit rate limiter when there are too many messages to edit!
                    await messages_reversed[idx].edit(content='', embed=embed)

        except Exception:
            logging.error('Failed to update the server info channel', exc_info=True)


async def update_presence_player_count(bot: lightbulb.BotApp, 
                                       servers: ServerCollection) -> None:
    """Update bot's status message with the current player count."""

    total_players: int = servers.get_total_players()
    presence_text: str = '{num} player{s} online'.format(num=total_players, s='s' if total_players != 1 else '')

    try:
        await bot.update_presence(activity=hikari.Activity(type=hikari.ActivityType.WATCHING, name=presence_text))

    except Exception:
        logging.error('Failed to update presence', exc_info=True)


async def update_server_info_channel(servers: ServerCollection, 
                             channel: hikari.TextableChannel) -> None:
    """Update or post server list to the specified channel."""

    board: BulletinBoard = BulletinBoard()
    embed: hikari.Embed = hikari.Embed(title='Darkest Hour: Europe \'44-\'45 Servers', 
                                       description=f'Updated <t:{int(time.time())}:R>.\n\u2800')

    # Build the server list
    if servers:
        sorted_servers = sorted(servers, key=lambda x: x.players, reverse=True)
        for s in sorted_servers:
            if s.is_online:
                status_emoji: str = ':green_circle:' if s.players > 0 else ':yellow_circle:'
                map: str = s.map.replace('DH-', '').replace('_', ' ')
                embed.add_field(name=f'{status_emoji} {s.name}', 
                                value=f'**Players**\t`{s.players} / {s.max_players}`\n**Map**\t`{map}`\n\u2800')
    elif embed.description:
        embed.description += '\nServers are down for maintenance...'

    board.add_embed(embed)
    await board.push_to_channel(channel)


async def fetch_server_info_channel() -> hikari.TextableChannel | None:
    """Fetch the channel where the server list will be posted"""

    conf: ServerBrowserSettings = darklight_bot.config.server_browser

    try: 
        channel: hikari.PartialChannel = await plugin.bot.rest.fetch_channel(conf.channel)

        if isinstance(channel, hikari.TextableChannel):
            logging.info(f'Fetched server info channel #{channel.name} ({channel.id})')
            return channel
        else:
            logging.error('Server info channel {conf.channel} is not a textable channel!')

    except hikari.NotFoundError:
        logging.error(f'Server info channel {conf.channel} doesn\'t exist.')

    except Exception:
        logging.error(f'Failed to fetch server info channel {conf.channel}', exc_info=True)

    return None


@plugin.listener(hikari.StartedEvent)
async def on_ready(_: hikari.StartedEvent) -> None:
    conf: ServerBrowserSettings = darklight_bot.config.server_browser
    servers: ServerCollection = ServerCollection([ Server((s.address, s.query_port), s.name) for s in conf.servers ])
    board_channel: hikari.TextableChannel | None = await fetch_server_info_channel()

    @tasks.task(s=conf.query_interval, pass_app=True)
    async def update_server_info_task(bot: lightbulb.BotApp) -> None:
        """Task responsible for updating server info."""

        # QUERY SERVERS

        try:
            await servers.update()
        except Exception:
            logging.error('Failed to query servers', exc_info=True)

            # Clear presence if update fails (we don't want to display stale player counts).
            try:
                await bot.update_presence(activity=None)
            except Exception: 
                logging.error('Failed to clear bot\'s presence')
            finally:
                return
        
        # UPDATE INFO

        await update_presence_player_count(bot, servers)

        if board_channel:
            await update_server_info_channel(servers, board_channel)

    update_server_info_task.start()


def load(bot: lightbulb.BotApp) -> None:
    bot.add_plugin(plugin)


def unload(bot: lightbulb.BotApp) -> None:
    bot.remove_plugin(plugin)
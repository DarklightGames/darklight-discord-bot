from typing import Sequence, Iterator

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
        self.info: unreal_query.ServerInfo = None
        self.players: int = 0
        self.max_players: int = 0
        self.map: str = ''
        self.failed_updates: int = 0
        self.is_online: bool = False

    async def update(self) -> None:
        self.info: unreal_query.ServerInfo | None = await unreal_query.query(self.addr)

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
        self.embeds: Sequence[hikari.Embed] = []


    def add_embed(self, embed: hikari.Embed) -> None:
        """Adds an embed to be published on the board"""
        self.embeds.append(embed)


    async def push_to_channel(self, channel: hikari.TextableChannel):
        """Modifies bot's latest messages with current embeds. New messages are created if necessary."""
        my_id = plugin.bot.get_me().id
        messages = [ x for x in await plugin.bot.rest.fetch_messages(channel) if x.author.id == my_id ]
        
        messages_to_edit = list(reversed(messages[:len(self.embeds)]))

        for idx, embed in enumerate(self.embeds):
            if idx >= len(messages_to_edit):
                await channel.send(content='', embed=embed)
            else:
                # WARNING: Hitting rate limiter when there are too many messages to edit!
                await messages_to_edit[idx].edit(content='', embed=embed)


@plugin.listener(hikari.StartedEvent)
async def on_ready(_: hikari.StartedEvent):
    conf: ServerBrowserSettings = darklight_bot.config.server_browser
    servers = ServerCollection([ Server((s.address, s.query_port), s.name) for s in conf.servers])
    board_channel = await plugin.bot.rest.fetch_channel(conf.channel)

    @tasks.task(s=conf.query_interval, pass_app=True)
    async def update_server_info(bot: lightbulb.BotApp) -> None:
        """Fetches player counts from the game servers and updates bot's status."""

        await servers.update()

        # Update presence
        total_players = servers.get_total_players()
        presence_text = '{num} player{s} online'.format(num=total_players, s='s' if total_players != 1 else '')
        await bot.update_presence(activity=hikari.Activity(type=hikari.ActivityType.WATCHING, name=presence_text))

        # Update servers channel
        board = BulletinBoard()
        embed = hikari.Embed(title='Darkest Hour: Europe \'44-\'45 Servers', 
                             description=f'Updated <t:{int(time.time())}:R>.\n\u2800')

        if servers:
            sorted_servers = sorted(servers, key=lambda x: x.players, reverse=True)
            for s in sorted_servers:
                if s.is_online:
                    status_emoji = ':green_circle:' if s.players > 0 else ':yellow_circle:'
                    map = s.map.replace('DH-', '').replace('_', ' ')
                    embed.add_field(name=f'{status_emoji} {s.name}', 
                                    value=f'**Players**\t`{s.players} / {s.max_players}`\n**Map**\t`{map}`\n\u2800')
        else:
            try:
                embed.description += '\nServers are down for maintenance...'
            except AttributeError:
                return

        board.add_embed(embed)
        await board.push_to_channel(board_channel)

    update_server_info.start()


def load(bot: lightbulb.BotApp) -> None:
    bot.add_plugin(plugin)


def unload(bot: lightbulb.BotApp) -> None:
    bot.remove_plugin(plugin)
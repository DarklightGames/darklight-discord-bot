import hikari
from typing import Sequence

class BulletinBoard():
    """A class for publishing embeds into multiple persistent messages and keeping them updated"""

    def __init__(self, bot: hikari.GatewayBot) -> None:
        self.embeds: Sequence[hikari.Embed] = []
        self.bot = bot


    def add_embed(self, embed: hikari.Embed) -> None:
        """Adds an embed to be published on the board"""
        self.embeds.append(embed)


    async def push_to_channel(self, channel: hikari.TextableChannel):
        """Modifies bot's latest messages with current embeds. New messages are created if necessary."""
        my_id = self.bot.get_me().id
        messages = [ x for x in await self.bot.rest.fetch_messages(channel) if x.author.id == my_id ]
        
        messages_to_edit = list(reversed(messages[:len(self.embeds)]))

        for idx, embed in enumerate(self.embeds):
            if idx >= len(messages_to_edit):
                await channel.send(content='', embed=embed)
            else:
                # WARNING: Hitting rate limiter when there are too many messages to edit!
                await messages_to_edit[idx].edit(content='', embed=embed)
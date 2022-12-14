import os
import logging

import hikari
from hikari.impl.config import CacheSettings
from hikari.api.config import CacheComponents
from hikari import Intents
import lightbulb
from lightbulb.ext import tasks
import bot as darklight_bot


def create_bot() -> lightbulb.BotApp:
    with open('./secrets/token') as f:
        token = f.read().strip()

    cache_settings = CacheSettings(components=CacheComponents.ALL)
    intents = Intents.GUILDS | Intents.GUILD_MEMBERS

    # Create the bot instance
    bot = lightbulb.BotApp(token=token,
                           intents=intents,
                           cache_settings=cache_settings)

    tasks.load(bot)

    # Load extensions
    bot.load_extensions_from('./bot/extensions')

    return bot


if __name__ == '__main__':
    if os.name != 'nt':
        import uvloop
        uvloop.install()

    create_bot().run()

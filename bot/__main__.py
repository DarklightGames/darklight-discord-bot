import os

import hikari
import lightbulb
from lightbulb.ext import tasks
import bot as darklight_bot


def create_bot() -> lightbulb.BotApp:
    with open('./secrets/token') as f:
        token = f.read().strip()

    # Create the bot instance
    bot = lightbulb.BotApp(token=token,
                           intents=hikari.Intents.NONE)

    tasks.load(bot)

    # Load extensions
    bot.load_extensions_from('./bot/extensions')

    return bot


if __name__ == '__main__':
    if os.name != 'nt':
        import uvloop
        uvloop.install()

    create_bot().run()

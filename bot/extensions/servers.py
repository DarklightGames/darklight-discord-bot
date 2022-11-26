import lightbulb
from lightbulb.ext import tasks
from hikari import Activity, ActivityType

import bot as darklight_bot
from bot.utils import unreal_query


plugin = lightbulb.Plugin('Servers')


@tasks.task(s=darklight_bot.SERVER_QUERY_INTERVAL_SECONDS, pass_app=True)
async def update_server_info(bot: lightbulb.BotApp) -> None:
    """Fetches player counts from the game servers and updates bot's status."""

    servers = await unreal_query.get(*darklight_bot.SERVERS)

    total_players = sum([s.players for s in servers if s != None])
    presence_text = '{num} player{s} online'.format(num=total_players, s='s' if total_players != 1 else '')

    await bot.update_presence(activity=Activity(type=ActivityType.WATCHING, name=presence_text))


def load(bot: lightbulb.BotApp) -> None:
    bot.add_plugin(plugin)
    update_server_info.start()


def unload(bot: lightbulb.BotApp) -> None:
    update_server_info.stop()
    bot.remove_plugin(plugin)

import hikari
from hikari import MessageFlag
import lightbulb
from lightbulb import commands
from bot.config import EventSettings
from bot import config
from collections import Counter
from functools import wraps
import bot as darklight_bot
import random
from typing import Any, Sequence


plugin = lightbulb.Plugin('EventRoster')


class AlreadyHasRole(Exception):
    """Member already has the requested role"""
    pass


ENLIST_MSG_1 = [
    'Guys, guys, you guys!',
    'This just in!',
    'A little birdy told me,',
    'Have you heard?',
    'Psst!',
    ''
]


ENLIST_MSG_2 = [
    '{member} has just signed up for **{team}** team.',
    '{member} has joined **{team}**.',
    '{member} is now enlisted with **{team}**.'
]


ENLIST_MSG_2_DEFECT = [
    '{member} has defected to **{team}**.',
    '{member} has left their team and joined **{team}**.',
]


ENLIST_MSG_3 = [
    'What a winner!',
    'The other team is now shambles.',
    'The enemy team is literally crying right now.',
    'What a champ!',
    'Hide your rations!',
    'An absolute asset!',
    'Buy him a drink!',
    'Don\'t tell anyone!',
    ''
]


def get_random_element(list: Sequence, skip_index: int | None = None) -> Any | None:
    return next(iter(random.sample(list, 1)), None)


def generate_enlist_message(defect: bool = False) -> str:
    msg: list[str] = []

    for part_choices in (ENLIST_MSG_1, ENLIST_MSG_2_DEFECT if defect else ENLIST_MSG_2, ENLIST_MSG_3):
        part = get_random_element(part_choices)
        if part:
            msg.append(part)

    return ' '.join(msg)


# def get_config(func):
#     @wraps(func)
#     def decorate(*args, ctx: lightbulb.context.Context, **kwargs):
#         guild = ctx.get_guild()
#         conf = config.guilds[guild.id].event_roster
#         return func(*args, ctx=ctx, event_conf=conf, **kwargs)

#     return decorate


async def assign_role(member: hikari.Member, role: hikari.Role) -> None:
    roles = member.get_roles()

    if role in roles:
        raise AlreadyHasRole
    else:
        await member.add_role(role)


async def remove_roles(member: hikari.Member, *role_ids: hikari.Role) -> None:
    member_role_ids = [ r.id for r in member.get_roles() ]
    roles_to_remove = set(role_ids).intersection(member_role_ids)
    for role in roles_to_remove:
        await member.remove_role(role)


async def remove_all_event_roles(member: hikari.Member, *roles: hikari.Role) -> None:
    conf: EventSettings = darklight_bot.config.event_roster
    await remove_roles(member, 
                       conf.axis_role,
                       conf.allied_role,
                       conf.sl_role)


def has_role(member: hikari.Member, role: hikari.Role) -> bool:
    try:
        return role in member.get_roles()
    except TypeError:
        return False


@lightbulb.option('team', 'Which team would you like to join?', choices=('Allies', 'Axis'))
@lightbulb.command('enlist', 'Join a team for the next event', guilds=[darklight_bot.config.guild])
@lightbulb.implements(commands.SlashCommand)
async def enlist(ctx: lightbulb.context.Context) -> None:
    team: str = ctx.options.team
    guild: hikari.Guild = ctx.get_guild()
    member: hikari.Member = guild.get_member(ctx.author.id)
    role_to_give: hikari.Role | None
    conf: EventSettings = darklight_bot.config.event_roster
    axis_role = guild.get_role(conf.axis_role)
    allied_role = guild.get_role(conf.allied_role)

    match team:
        case 'Axis':
            role_to_give = axis_role
        case 'Allies':
            role_to_give = allied_role

    try:
        await assign_role(member, role_to_give)
    except AlreadyHasRole:
        await ctx.respond(f'You\'re already on **{team}** team!', flags=MessageFlag.EPHEMERAL)
        return

    defected: bool = has_role(member, axis_role) | has_role(member, allied_role)

    await remove_all_event_roles(member)

    msg = generate_enlist_message(defected).format(member=ctx.author.mention, team=team)

    await ctx.respond(msg)


@lightbulb.command('leave-team', 'I want to quit my team', guilds=[darklight_bot.config.guild])
@lightbulb.implements(commands.SlashCommand)
async def leave_team(ctx: lightbulb.context.Context) -> None:
    guild: hikari.Guild = ctx.get_guild()
    member: hikari.Member = guild.get_member(ctx.author.id)

    await remove_all_event_roles(member)
    await ctx.respond(f'You\'ve quit your team!', flags=MessageFlag.EPHEMERAL)


@lightbulb.command('reserve-sl', 'I want to be a squad leader for the next event', guilds=[darklight_bot.config.guild])
@lightbulb.implements(commands.SlashCommand)
async def reserve_sl(ctx: lightbulb.context.Context) -> None:
    guild: hikari.Guild = ctx.get_guild()
    member: hikari.Member = guild.get_member(ctx.author.id)
    conf: EventSettings = darklight_bot.config.event_roster

    try:
        await assign_role(member, conf.sl_role)
    except AlreadyHasRole:
        await ctx.respond(f'You\'ve already volunteered to be a squad leader!', flags=MessageFlag.EPHEMERAL)
        return

    await ctx.respond(f'{ctx.author.mention} has volunteered to lead a squad. Don\'t forget to place rally points!')


@lightbulb.command('rescind-sl', 'I don\'t want to be a squad leader anymore. Take away my role', guilds=[darklight_bot.config.guild])
@lightbulb.implements(commands.SlashCommand)
async def rescind_sl(ctx: lightbulb.context.Context) -> None:
    guild: hikari.Guild = ctx.get_guild()
    member: hikari.Member = guild.get_member(ctx.author.id)
    conf: EventSettings = darklight_bot.config.event_roster

    if has_role(member, conf.sl_role):
        await remove_roles(member, conf.sl_role)
        await ctx.respond(f'{ctx.author.mention} no longer wants to lead a squad.')
    else:
        await ctx.respond(f'You\'re not a squad leader!', flags=MessageFlag.EPHEMERAL)


@lightbulb.command('roster', 'Show roster for the next event', guilds=[darklight_bot.config.guild], ephemeral=True)
@lightbulb.implements(commands.SlashCommand)
async def roster(ctx: lightbulb.context.Context) -> None:
    guild: hikari.Guild = ctx.get_guild()
    embed = hikari.Embed(title='Event Roster')
    members = [ m[1] for m in guild.get_members().items() ]
    conf: EventSettings = darklight_bot.config.event_roster
    squad_leaders = set(m for m in members if has_role(m, guild.get_role(conf.sl_role)))

    # TODO: REFACTOR THIS MESS!

    # AXIS
    axis_members = [ m for m in members if has_role(m, guild.get_role(conf.axis_role)) ]

    axis_squad_leaders = squad_leaders.intersection(axis_members)
    if axis_squad_leaders:
        axis_squad_leaders_text = '\n'.join([ m.username for m in axis_squad_leaders ])
    else:
        axis_squad_leaders_text = '-NONE-'

    axis_rest = [*(Counter(axis_members) - Counter(axis_squad_leaders)).elements()]

    if axis_rest:
        axis_rest_text = '\n'.join([ m.username for m in axis_rest ])
    else:
        axis_rest_text = '-NONE-'

    embed.add_field(name='Axis', 
                    value=f'```yaml\nSquad Leaders:\n{axis_squad_leaders_text}\n\nMembers:\n{axis_rest_text}\n\nTotal: {len(axis_members)}```', 
                    inline=True)

    # ALLIES
    allied_members = [ m for m in members if has_role(m, guild.get_role(conf.allied_role)) ]

    allied_squad_leaders = squad_leaders.intersection(allied_members)

    if allied_squad_leaders:
        allied_squad_leaders_text = '\n'.join([ m.username for m in allied_squad_leaders ])
    else:
        allied_squad_leaders_text = '-NONE-'

    allied_rest = [*(Counter(allied_members) - Counter(allied_squad_leaders)).elements()]

    if allied_rest:
        allied_rest_text = '\n'.join([ m.username for m in allied_rest ])
    else:
        allied_rest_text = '-NONE-'

    embed.add_field(name='Allies', 
                    value=f'```yaml\nSquad Leaders:\n{allied_squad_leaders_text}\n\nMembers:\n{allied_rest_text}\n\nTotal: {len(allied_members)}```', 
                    inline=True)

    await ctx.respond(embed=embed)


def load(bot: lightbulb.BotApp) -> None:
    bot.add_plugin(plugin)
    bot.command(enlist)
    bot.command(leave_team)
    bot.command(reserve_sl)
    bot.command(rescind_sl)
    bot.command(roster)


def unload(bot: lightbulb.BotApp) -> None:
    remove_commands = ['enlist',
                       'leave-team',
                       'reserve-sl',
                       'rescind-sl',
                       'roster']

    for cmd_name in remove_commands:
        command = bot.get_slash_command(cmd_name)
        if command is not None:
            bot.remove_command(command)

    bot.remove_plugin(plugin)
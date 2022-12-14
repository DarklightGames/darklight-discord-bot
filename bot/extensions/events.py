import hikari
from hikari import MessageFlag
import lightbulb
from lightbulb import commands
import bot as darklight_bot
from bot.utils.bulletin import BulletinBoard
from lightbulb.ext import tasks
import datetime as dt
from collections import Counter

plugin = lightbulb.Plugin('Events')


GUILDS=[1044732831710056639]
ROSTER_CHANNEL=1050800193009876992
AXIS_ROLE_ID=1050774810529112175
ALLIES_ROLE_ID=1050774864136507462
SQUAD_LEADER_ROLE_ID=1050774895019171860


class AlreadyHasRole(Exception):
    """Member already has the requested role"""
    pass


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
    await remove_roles(member, AXIS_ROLE_ID, ALLIES_ROLE_ID, SQUAD_LEADER_ROLE_ID)


def has_role(member: hikari.Member, role: hikari.Role) -> bool:
    try:
        return role in member.get_roles()
    except TypeError:
        return False


@lightbulb.option('team', 'Which team would you like to join?', choices=('Allies', 'Axis'))
@lightbulb.command('enlist', 'Join a team for the next event', guilds=GUILDS)
@lightbulb.implements(commands.SlashCommand)
async def enlist(ctx: lightbulb.context.Context) -> None:
    team: str = ctx.options.team
    guild: hikari.Guild = ctx.get_guild()
    member: hikari.Member = guild.get_member(ctx.author.id)
    role_to_give: hikari.Role | None

    match team:
        case 'Axis':
            role_to_give = guild.get_role(AXIS_ROLE_ID)
        case 'Allies':
            role_to_give = guild.get_role(ALLIES_ROLE_ID)

    try:
        await assign_role(member, role_to_give)
    except AlreadyHasRole:
        await ctx.respond(f'You\'re already on **{team}** team!', flags=MessageFlag.EPHEMERAL)
        return

    await remove_all_event_roles(member)
    await ctx.respond(f'{ctx.author.mention} has joined **{team}**!')


@lightbulb.command('leave-team', 'I want to quit my team', guilds=GUILDS)
@lightbulb.implements(commands.SlashCommand)
async def leave_team(ctx: lightbulb.context.Context) -> None:
    guild: hikari.Guild = ctx.get_guild()
    member: hikari.Member = guild.get_member(ctx.author.id)

    await remove_all_event_roles(member)
    await ctx.respond(f'You\'ve quit your team!', flags=MessageFlag.EPHEMERAL)


@lightbulb.command('reserve-sl', 'I want to be a squad leader for the next event', guilds=GUILDS)
@lightbulb.implements(commands.SlashCommand)
async def reserve_sl(ctx: lightbulb.context.Context) -> None:
    guild: hikari.Guild = ctx.get_guild()
    member: hikari.Member = guild.get_member(ctx.author.id)

    try:
        await assign_role(member, guild.get_role(SQUAD_LEADER_ROLE_ID))
    except AlreadyHasRole:
        await ctx.respond(f'You\'ve already volunteered to be a squad leader!', flags=MessageFlag.EPHEMERAL)
        return

    await ctx.respond(f'{ctx.author.mention} has volunteered to be a squad leader. Don\'t forget to place rally points!', flags=MessageFlag.EPHEMERAL)


@lightbulb.command('rescind-sl', 'I don\'t want to be a squad leader anymore. Take away my role', guilds=GUILDS)
@lightbulb.implements(commands.SlashCommand)
async def rescind_sl(ctx: lightbulb.context.Context) -> None:
    guild: hikari.Guild = ctx.get_guild()
    member: hikari.Member = guild.get_member(ctx.author.id)

    if has_role(member, SQUAD_LEADER_ROLE_ID):
        await remove_roles(member, SQUAD_LEADER_ROLE_ID)
        await ctx.respond(f'{ctx.author.mention} no longer wants to lead a squad.')
    else:
        await ctx.respond(f'You\'re not a squad leader!', flags=MessageFlag.EPHEMERAL)


@lightbulb.command('show-roster', 'Show roster for the next event', guilds=GUILDS, ephemeral=True)
@lightbulb.implements(commands.SlashCommand)
async def roster(ctx: lightbulb.context.Context) -> None:
    guild: hikari.Guild = ctx.get_guild()
    embed = hikari.Embed(title='Event Roster')
    members = [ m[1] for m in guild.get_members().items() ]
    squad_leaders = set(m for m in members if has_role(m, guild.get_role(SQUAD_LEADER_ROLE_ID)))

    # TODO: REFACTOR THIS MESS!

    # AXIS
    axis_members = [ m for m in members if has_role(m, guild.get_role(AXIS_ROLE_ID)) ]

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
    allied_members = [ m for m in members if has_role(m, guild.get_role(ALLIES_ROLE_ID)) ]

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


# @plugin.listener(hikari.StartedEvent)
# async def on_ready(_: hikari.StartedEvent):
#     board_channel = await plugin.bot.rest.fetch_channel(ROSTER_CHANNEL)

#     @tasks.task(s=5, pass_app=True)
#     async def update_roster_info(bot: lightbulb.BotApp) -> None:
#         # Update servers channel
#         board = BulletinBoard(bot)
#         allies_embed = hikari.Embed(title='AXIS')
#         axis_embed = hikari.Embed(title='ALLIES')

#         board.add_embed(allies_embed)
#         board.add_embed(axis_embed)
#         await board.push_to_channel(board_channel)

    # update_roster_info.start()


def load(bot: lightbulb.BotApp) -> None:
    bot.add_plugin(plugin)
    bot.command(enlist)
    bot.command(leave_team)
    bot.command(reserve_sl)
    bot.command(rescind_sl)
    bot.command(roster)


def unload(bot: lightbulb.BotApp) -> None:
    bot.remove_command(bot.get_slash_command('enlist'))
    bot.remove_command(bot.get_slash_command('leave-team'))
    bot.remove_command(bot.get_slash_command('reserve-sl'))
    bot.remove_command(bot.get_slash_command('rescind-sl'))
    bot.remove_command(bot.get_slash_command('roster'))
    bot.remove_plugin(plugin)
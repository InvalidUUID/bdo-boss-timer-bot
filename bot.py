'''Main bot file!!~!~!!!'''

import asyncio
from os import getenv
import io
import json
from datetime import datetime, timedelta
import discord
from discord.ext import commands


async def print_boss_message(boss_name, channel, delta):
    '''Print the "boss is spawning" notification'''
    if len(boss_name) == 1:
        await channel.send('{boss[0].mention} spawns in {delta} minutes'.format(
            boss=boss_name, delta=delta))
    elif len(boss_name) == 2:
        await channel.send(
            '{boss[0].mention} and {boss[1].mention} will spawn in {delta} minutes'
            .format(boss=boss_name, delta=delta))


def boss_descrip(boss):
    '''Build the boss description'''
    return str('Spawns at {location}'.format(location=boss['location']))


async def print_next_boss_message(boss_name, boss_time, channel, is_today):
    '''Prints the bot embed for the nextboss command'''
    # need to convert utc "boss_time" time of day to be either that time today,
    #   or that time tomorrow
    # split boss_time from HH:MM into ['HH', 'MM'] and then into [HH, MM] as ints
    boss_time_tokens = list(map(int, boss_time.split(':')))
    # use boolean to advance time, if needed
    when = datetime.utcnow() + timedelta(days=(0 if is_today else 1))
    # force boss_time onto when
    when = when.replace(hour=boss_time_tokens[0], minute=boss_time_tokens[1])

    embed = discord.Embed(timestamp=when, color=boss_name[0]['color'])
    embed.set_footer(text='Spawns', icon_url='https://i.imgur.com/6qzL6l4.png')
    embed.set_thumbnail(url=boss_name[0]['avatar'])

    for boss in boss_name:
        embed.add_field(name=boss['name'], value='{spawn}\n\n**Recommendations:**\n{recommendations}\n\n**Valuable Drops:**\n{drops}\n\n:link: [More Boss Info]({link})'
            .format(
                spawn=boss_descrip(boss), recommendations=boss['recommendations'], link=boss['link'], drops=boss['drops']
            ), inline=False)


    # Add all the boss information, first names & spawn locations
    # for boss in boss_name:
    #     embed.add_field(name=boss['name'], value=boss_descrip(boss), inline=True)

    # then a blank line to force inline to wrap
    # embed.add_field(name='\u200b', value='\u200b', inline=False)

    # Then fight recommendations
    # for boss in boss_name:
    #     embed.add_field(name='Recommendations', value=boss['recommendations']
    #                     + '\n:link: [More Boss Info]({link})'.format(
    #                         link=boss['link']), inline=True)

    # another separator
    # embed.add_field(name='\u200b', value='\u200b', inline=False)

    # then drops
    # for boss in boss_name:
    #     embed.add_field(name='Valuable Drops', value=boss['drops'], inline=True)

    # await channel.send(embed=embed)


BOSS_SCHEDULE = json.loads(io.open('boss_schedule.json', 'r').read())
BOSS_DATA = json.loads(io.open('boss_strings.json', 'r').read())
DESCRIPTION = 'A Bot for managing Boss Spawn Alerts for Black Desert Online'
BOT = commands.Bot(command_prefix='.', description=DESCRIPTION)
TOKEN = getenv('BOT_TOKEN')

CHANNEL_ID = int(getenv('CHANNEL_ID'))
GUILD_ID = int(getenv('GUILD_ID'))


@BOT.event
async def on_ready():
    '''
    Print that the bot is ready when it's done building,
    and assign settings from env vars
    '''
    print('Bot ID is: [', BOT.user.id, ']')
    print('Bot Name is: [', BOT.user.name, ']')
    print('───────────────────────────────────────────')
    print('Waiting for build to finish...')
    print('Build completed, bot is now running.')
    print('───────────────────────────────────────────')
    print('I\'m currently on the following server(s): ')
    for guild in BOT.guilds:
        print(guild)
        if guild.id == GUILD_ID:
            channel = discord.utils.get(guild.channels, id=CHANNEL_ID)
            BOT.bg_task = BOT.loop.create_task(background_task(channel, guild))


@BOT.command()
async def ping(ctx):
    '''Ping! Use this to check if the bot is responsiding to commands.'''
    await ctx.send('_pong_')


@BOT.command()
async def addme(ctx, *, boss_name):
    '''Adds you to the notification list for when a specific boss spawns.'''
    user = ctx.message.author
    try:
        role = discord.utils.get(ctx.guild.roles, name=boss_name)
        if role is not None:
            await user.add_roles(role)
            await ctx.send('You will be notified when **{boss_name}** spawns :)'.format(boss_name=boss_name))
        else:
            await ctx.send('Please check that you\'ve spelled the boss name correctly and try again.')
    except KeyError:
        ctx.send('Please check that you\'ve spelled the boss name correctly and try again.')
    # user = ctx.message.author
    # role = discord.utils.get(ctx.guild.roles, name='Boss Timer')
    # await user.add_roles(role)
    # await ctx.send('You will now be notified when the next boss spawns :)')


@BOT.command()
async def removeme(ctx, *, boss_name):
    '''Removes you from notification list for when a boss spawns.'''
    user = ctx.message.author
    try:
        role = discord.utils.get(ctx.guild.roles, name=boss_name)
        if role is not None:
            await user.remove_roles(role)
            await ctx.send('You will no longer be notified when **{boss_name}** spawns :('.format(boss_name=boss_name))
        else:
            await ctx.send('Please check that you\'ve spelled the boss name correctly and try again.')
    except KeyError:
        ctx.send('Please check that you\'ve spelled the boss name correctly and try again.')
    # role = discord.utils.get(ctx.guild.roles, name='Boss Timer')
    # await user.remove_roles(role)
    # await ctx.send('You will no longer be notified when the next boss spawns :(')


@BOT.command()
async def setchannel(ctx):
    '''Define what channel the bot will send boss spawn notifications to.'''
    channel = ctx.message.channel
    guild = ctx.message.guild
    BOT.bg_task = BOT.loop.create_task(background_task(channel, guild))
    await ctx.send('I will send boss notifications to {0.mention}'.format(channel))


@BOT.command()
async def stopnotifs(ctx):
    '''Stop the bot from sending boss spawn notications'''
    if BOT.bg_task:
        BOT.bg_task.cancel()
        try:
            await BOT.bg_task
        except asyncio.CancelledError:
            print('Background task was sucessfully stopped.')
        finally:
            pass
    await ctx.send('Okay, I\'ll stop sending spawn notifications.')


@BOT.command()
async def nextboss(ctx):
    '''Tells you which boss spawns next, and at what time it will spawn.'''
    try:
        print('running nextboss...')
        channel = ctx.message.channel

        current_time = datetime.utcnow()
        current_hour = datetime.strftime(current_time, "%H:%M")
        current_day = datetime.strftime(current_time, "%a")
        next_day = datetime.strftime(current_time + timedelta(days=1), "%a")

        hour = None
        for hour in BOSS_SCHEDULE.keys():
            if current_hour < hour:
                next_boss_spawn = BOSS_SCHEDULE[hour][current_day]
                is_today = True
                break
            # if there is no boss to spawn on the current day
            # then it should be the first boss of the next day
            next_boss_spawn = BOSS_SCHEDULE['00:00'][next_day]
            is_today = False

        boss_names = []
        for boss in next_boss_spawn:
            boss_names.append(BOSS_DATA[boss])

        await print_next_boss_message(boss_names, hour, channel, is_today)
    except Exception as e:
        print(e)


@BOT.command()
async def setup(ctx):
    '''Adds roles to your server that the bot will use to notify members about boss spawns.'''
    for name in BOSS_DATA:
        role = discord.utils.get(ctx.guild.roles, name=name)
        if role is None:
            guild = ctx.guild
            await guild.create_role(name=name)
        else:
            await ctx.send('A {role} role already exists.')


@BOT.command()
async def cleanup(ctx):
    '''Remove roles from your server that the bot created to notify members about boss spawns.'''


async def check_x_ahead(current_time, time_ahead, channel, guild):
    '''Generically check ahead X minutes for the next boss'''
    current_hour = datetime.strftime(current_time, "%H:%M")
    current_day = datetime.strftime(current_time, "%a")
    current_hour_px = datetime.strftime(current_time + timedelta(minutes=time_ahead), "%H:%M")

    # fmt = 'Current day: {current_day} | Current time: {current_time} ' +
    #   '| Current+{x}: {current_hour_px}'
    # print(fmt.format(
    #   current_time=current_hour, current_hour_px=current_hour_px,
    #   current_day=current_day, x=time_ahead))

    next_boss_spawn = []
    for hour in BOSS_SCHEDULE.keys():
        if current_hour < hour == current_hour_px:
            delta = datetime.strptime(hour, "%H:%M") - datetime.strptime(current_hour, "%H:%M")
            next_boss_spawn = BOSS_SCHEDULE[hour][current_day]
            for boss in next_boss_spawn:
                print(boss)
            break

    if len(next_boss_spawn) >= 1:
        print('The next boss that will spawn is...')
        boss_names = []

        for boss in next_boss_spawn:
            print(boss)
            boss_names.append((discord.utils.get(guild.roles, name=boss)))

        await print_boss_message(boss_names, channel, int(delta.seconds/60))


@BOT.event
async def background_task(channel, guild):
    '''Background task for checking for the next spawning boss'''
    await BOT.wait_until_ready()
    print('───────────────────────────────────────────')
    print('Bot is Ready, background task is running')
    while not BOT.is_closed():
        try:
            current_time = datetime.utcnow()
            await check_x_ahead(current_time, 10, channel, guild)
            await check_x_ahead(current_time, 30, channel, guild)
        except Exception as exception:
            print(exception)

        await asyncio.sleep(60)  # task runs every 60 seconds

BOT.run(TOKEN)

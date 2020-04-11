from datetime import datetime, timedelta
import io
import asyncio
import discord
from discord.ext import commands
from os import getenv

async def print_boss_message(boss_name,role,channel,delta):
    if len(boss_name) == 1:
        await channel.send('{role.mention} - {boss[0].mention} will spawn in {delta}min'.format(role=role,boss=boss_name,delta=delta))
    elif len(boss_name) == 2:
        await channel.send('{role.mention} - {boss[0].mention} and {boss[1].mention} will spawn in {delta}min'.format(role=role,boss=boss_name,delta=delta))

def join_bosses(bosses):
    return list(map(lambda boss: boss.mention, bosses))

async def print_next_boss_message(boss_name,boss_time,channel,is_today):
    # need to convert utc "boss_time" time of day to be either that time today, or that time tomorrow
    # split boss_time from HH:MM into ['HH', 'MM'] and then into [HH, MM] as ints
    boss_time_tokens = list(map(lambda t : int(t), boss_time.split(':')))
    # use boolean to advance time, if needed
    when = datetime.utcnow() + timedelta(days=(0 if is_today else 1))
    # force boss_time onto when
    when = when.replace(hour=boss_time_tokens[0], minute=boss_time_tokens[1])
    
    embed = discord.Embed(description = ", ".join(join_bosses(boss_name)), timestamp = when)
    embed.set_footer(text='Spawns', icon_url='https://i.imgur.com/6qzL6l4.png')
    embed.set_author(name='Karanda', icon_url='https://i.imgur.com/HOhqj1w.png')
    await channel.send(embed=embed)

file = io.open("boss_schedule.txt","r").read()
boss_schedule = eval(file)

description = 'Bot for managing boss alerts'
bot = commands.Bot(command_prefix='.', description=description)
token = getenv('BOT_TOKEN')

@bot.event
async def on_ready():
    print('Bot ID: ', bot.user.id)
    print('Bot name: ', bot.user.name)
    print('---------------')
    print('This bot is ready for action!')
    print('I\'m currently on those servers: ')
    for guild in bot.guilds:
        print(guild)

@bot.command()
async def ping(ctx):
    '''Ping!'''
    await ctx.send('_pong_')

@bot.command()
async def notifyme(ctx):
    '''Add your name to the list of notifications'''
    user = ctx.message.author
    role = discord.utils.get(ctx.guild.roles, name='Boss Timer')
    await user.add_roles(role)
    await ctx.send('You will now be notified when the next boss spawns :)')

@bot.command()
async def removeme(ctx):
    '''Remove your name from the list of notications'''
    user = ctx.message.author
    role = discord.utils.get(ctx.guild.roles, name='Boss Timer')
    await user.remove_roles(role)
    await ctx.send('You will no longer be notified when the next boss spawns :(')

@bot.command()
async def setchannel(ctx):
    '''Define what channel the bot will send notifications to'''
    channel = ctx.message.channel
    guild = ctx.message.guild
    role = discord.utils.get(ctx.guild.roles, name='Boss Timer')
    bot.bg_task = bot.loop.create_task(background_task(channel,guild,role))
    await ctx.send('I will send boss notifications to {0.mention}'.format(channel))

@bot.command()
async def stoppls(ctx):
    '''Stop the bot from sending notications'''
    if bot.bg_task:
        bot.bg_task.cancel()
        try:
            await bot.bg_task
        except asyncio.CancelledError:
            print('Task was sucessfully canceled')
        finally:
            pass
    await ctx.send('Okay, I\'ll stop...')

@bot.command()
async def nextboss(ctx):
    '''Says what the next boss is'''
    channel = ctx.message.channel
    guild = ctx.message.guild

    current_time = datetime.utcnow()
    current_hour = datetime.strftime(current_time,"%H:%M")
    current_day = datetime.strftime(current_time,"%a")
    next_day = datetime.strftime(current_time + timedelta(days=1),"%a")

    for hour in boss_schedule.keys():
        if current_hour < hour:
            next_boss_spawn = boss_schedule[hour][current_day]
            is_today = True
            break
        # if there is no boss to spawn on the current day
        # then it should be the first boss of the next day
        next_boss_spawn = boss_schedule['00:00'][next_day]
        is_today = False
        
    boss_names = []
    for boss in next_boss_spawn:
        boss_names.append((discord.utils.get(guild.roles, name=boss)))

    await print_next_boss_message(boss_names,hour,channel,is_today)

@bot.event
async def background_task(channel,guild,role):
    await bot.wait_until_ready()
    print('Bot is ready')
    while not bot.is_closed():
        current_time = datetime.utcnow()
        current_hour = datetime.strftime(current_time,"%H:%M")
        current_hour_p5 = datetime.strftime(current_time + timedelta(minutes=5),"%H:%M")
        current_day = datetime.strftime(current_time,"%a")

        print('Current time: {current_time} | Current+5: {current_hour_p5}'.format(current_time=current_hour,current_hour_p5=current_hour_p5))

        next_boss_spawn = []
        for hour in boss_schedule.keys():
            if current_hour < hour <= current_hour_p5:
                delta = strptime(hour,"%H:%M") - strptime(current_hour,"%H:%M")
                next_boss_spawn = boss_schedule[hour][current_day]
                break
        
        print('Next boss found is...')

        if next_boss_spawn:
            boss_names = []

            for boss in next_boss_spawn:
                print(boss)
                boss_names.append((discord.utils.get(guild.roles, name=boss)))

            await print_boss_message(boss_names,role,channel,int(delta.seconds/60))

        await asyncio.sleep(60) # task runs every 60 seconds

bot.run(token)

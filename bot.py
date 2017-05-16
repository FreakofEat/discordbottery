# import discord
from discord.ext import commands
import asyncio
import configparser
import random
from cogs import general, games, voice, queries, twitter, markov, tasks
import os
import psycopg2
import urllib.parse

# Store useful config vars
config = configparser.ConfigParser()
config.read('config')
command_trigger = config['messages']['commandTrigger']
custom_trigger = config['messages']['customTrigger']

# Bot vars
c_prefixes = ['`']
description = '''
fun entertainment
'''
# help_attrs = dict()
bot = commands.Bot(command_prefix=c_prefixes, description=description)

conn = None
def connect_to_postgres():
    """ Connects to the postgres server storing custom vars + bank(?)"""
    # Postgres
    global conn
    urllib.parse.uses_netloc.append("postgres")
    url = urllib.parse.urlparse(str(os.environ["DATABASE_URL"]))
    conn = psycopg2.connect(
        database=url.path[1:],
        user=url.username, password=url.password,
        host=url.hostname, port=url.port
    )

# General global vars
c_commands = {} # Stored custom commands from database

@bot.event
async def on_message(message):
    """ Every message received goes through here """
    # handles custom commands first, just fun stuff over here
    await react_world(message)
    if message.author.id == bot.user.id:
        return
    if message.content == '':
        return
    elif message.content.startswith(custom_trigger):
        await custom_command_check(message)
    elif message.content.lower() == 'witness me':
        await bot.send_message(message.channel, "WITNESSED")
    elif message.content.lower() == 'cut my life':
        await bot.send_message(message.channel, "INTO PIECES")
        await asyncio.sleep(3)
        await bot.send_message(message.channel, "THIS IS MY LAST RESORT")
    elif message.content.lower() == 'damn':
        await bot.add_reaction(message, "🇩")
        await bot.add_reaction(message, "🇦")
        await bot.add_reaction(message, "🇳")
        await bot.add_reaction(message, "🇮")
        await bot.add_reaction(message, "🇪")
        await bot.add_reaction(message, "🇱")
        if random.randint(0, 100) == 72:
            await bot.add_reaction(message, "‼")
    elif message.content.lower() == '<:d_:309110665941876736>amn':
        if message.server.id != '144849743368028160':
            return
        await bot.send_message(message.channel, "<:d_:309110665941876736>aniel")
    elif message.content.lower() in ('huda', 'hudda'): #TBH Not sure how it's spelled
        await bot.send_message(message.channel, "hecc")
    elif message.content.lower().find('vmboys') != -1:
        if random.randint(0, 1) == 0:
            await bot.send_message(message.channel, "_WHEEZE_")
        else:
            await bot.send_message(message.channel, "haha, nice")
    elif message.content.lower().find('cuck') != -1:
        await bot.add_reaction(message, "😳")
    # discordpy checks if the message is invoking a bot command and performs it
    await bot.process_commands(message)
    
async def react_world(message):
    """ adds a reaction to a message """
    if message.server.id != '144849743368028160':
        return
    # SORRY REACTION
    '''
    if 'tsun' in message.content.lower():
        emoji_list = message.server.emojis
        sorry_emoji = ':sorry:'
        for emoji in emoji_list:
            if 'sorry' in emoji.name.lower():
                sorry_emoji = emoji
        await bot.add_reaction(message, sorry_emoji)
    '''
    # GANG'S ALL HERE
    if 'gang' in message.content.lower():
        emoji_list = message.server.emojis
        for emoji in emoji_list: # Iterating to find all relevant emojis
            if 'gang' in emoji.name.lower():
                await bot.add_reaction(message, emoji)
    # tim
    if message.author.id == '185607847294271488':
        emoji_list = message.server.emojis
        tim = "timgasm"
        for emoji in emoji_list:
            if 'timgasm' in emoji.name.lower():
                await bot.add_reaction(message, emoji)

async def custom_command_check(message):
    """ checks for a custom command storing in the database and performs it"""
    query = message.content[1:]
    cur = conn.cursor()
    cur.execute("SELECT * FROM message_commands WHERE invoke = (%s)", [query])
    # command_details = c_commands.get(query[0])
    try:
        invoke, to_send, is_tts, idk = cur.fetchone()
    except TypeError:
        return
    cur.close()

    await bot.send_typing(message.channel)
    """ add custom message commands here """
    await bot.send_message(message.channel, to_send, tts=is_tts)
    # if arguments[0] == 'voice':
    #     await voice_command(arguments, message)

async def create_server_dirs():
    """ Creates dirs to store temp files for each server """
    for server in bot.servers:
        if not os.path.exists('data/' + server.name + ' - ' + server.id):
            os.mkdir('data/' + server.name + ' - ' + server.id)

async def add_to_bank(user_id):
    cur = conn.cursor()
    cur.execute("INSERT INTO bank (user_id, currency) VALUES (%s, 120) ON CONFLICT DO NOTHING", [user_id])
    conn.commit()
    cur.close()

async def bank_setup():
    cur = conn.cursor()
    for server in bot.servers:
        for user in server.members:
            cur.execute("SELECT * FROM bank WHERE user_id = (%s)", [user.id])
            if cur.fetchone() is None:
                print(user.id)
                await add_to_bank(user.id)
    print('bank setup')
    cur.close()

@bot.event
async def on_server_join(server):
    """ Creates a folder for the next server """
    if not os.path.exists('data/' + server.name + ' - ' + server.id):
        os.mkdir('data/' + server.name + ' - ' + server.id)


@bot.event
async def on_ready():
    """ When the bot is logged in and ready to take commands """
    print('logged in as: ' + bot.user.name)
    print('bot id: ' + bot.user.id)
    await create_server_dirs()
    # await bank_setup()


if __name__ == '__main__':
    if not os.path.exists('data'):
        os.mkdir('data')
    
    connect_to_postgres()
    
    bot.add_cog(general.General(bot))
    bot.add_cog(voice.Voice(bot))
    bot.add_cog(queries.Queries(bot))
    bot.add_cog(games.Games(bot, conn))
    bot.add_cog(twitter.Twitter(bot))
    bot.add_cog(markov.Markov(bot))
    
    task_obj = tasks.Tasks(bot)
    
    bot.loop.create_task(task_obj.zooboys())
    bot.loop.create_task(task_obj.who_up())
    bot.run(str(os.environ['DISCORD_TOKEN']))
    # Some cleanup if the bot is disconnected somehow
    queries.close_aiohttp()
    twitter.close_aiohttp()
    tasks.close_aiohttp()


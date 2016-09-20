# import discord
from discord.ext import commands
import asyncio
import configparser
import random
from cogs import general, games, voice, queries, twitter
import os
import psycopg2
import urllib.parse
import time


config = configparser.ConfigParser()
config.read('config')
# bot_token = config['discord']['BotToken']
command_trigger = config['messages']['commandTrigger']
custom_trigger = config['messages']['customTrigger']
# discord_token = os.environ['DISCORD_TOKEN']
# bing_key = os.environ['BING_API_KEY']

# Bot vars
c_prefixes = ['`']
description = '''
fun entertainment
'''
# help_attrs = dict()
bot = commands.Bot(command_prefix=c_prefixes, description=description)

# Postgres
urllib.parse.uses_netloc.append("postgres")
url = urllib.parse.urlparse(str(os.environ["DATABASE_URL"]))
conn = psycopg2.connect(
    database=url.path[1:],
    user=url.username, password=url.password,
    host=url.hostname, port=url.port
)

# General global vars
c_commands = {}


@bot.event
async def on_message(message):
    # handles custom commands first
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
        await bot.send_message(message.channel, "daniel")
    elif message.content.lower() in ('huda', 'hudda'): #TBH Not sure how it's spelled
        await bot.send_message(message.channel, "hecc")
    elif message.content.lower().find('vmboys') != -1:
        if random.randint(0, 1) == 0:
            await bot.send_message(message.channel, "_WHEEZE_")
        else:
            await bot.send_message(message.channel, "haha, nice")

    await bot.process_commands(message)


async def custom_command_check(message):
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

async def zooboys():
    await bot.wait_until_ready()
    while not bot.is_closed:
        cur_time = time.localtime()
        if cur_time.tm_hour == 17 and cur_time.tm_min == 48:
            await bot.send_message(bot.get_channel('144849743368028160'),
                                   '11:11 make a wish')
        await asyncio.sleep(60)

@bot.event
async def on_server_join(server):
    if not os.path.exists('data/' + server.name + ' - ' + server.id):
        os.mkdir('data/' + server.name + ' - ' + server.id)


@bot.event
async def on_ready():
    print('logged in as: ' + bot.user.name)
    print('bot id: ' + bot.user.id)
    await create_server_dirs()
    # await bank_setup()


if __name__ == '__main__':
    if not os.path.exists('data'):
        os.mkdir('data')

    bot.add_cog(general.General(bot))
    bot.add_cog(voice.Voice(bot))
    bot.add_cog(queries.Queries(bot))
    bot.add_cog(games.Games(bot, conn))
    bot.add_cog(twitter.Twitter(bot))

    bot.loop.create_task(zooboys())
    bot.run(str(os.environ['DISCORD_TOKEN']))

    queries.close_aiohttp()
    twitter.close_aiohttp()


# import discord
from discord.ext import commands
import asyncio
import configparser
import random
from cogs import general, games, voice
import os
import psycopg2
import urllib.parse


config = configparser.ConfigParser()
config.read('config')
# bot_token = config['discord']['BotToken']
command_trigger = config['messages']['commandTrigger']
# discord_token = os.environ['DISCORD_TOKEN']
# bing_key = os.environ['BING_API_KEY']

# Bot vars
prefixes = ['`', '?']
description = '''
fun entertainment
'''
# help_attrs = dict()
bot = commands.Bot(command_prefix=prefixes, description=description)

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
cur = conn.cursor()

@bot.event
async def on_message(message):
    # handles custom commands first
    # if message.author.id == client.user.id:
    #     return
    if message.content == '' or message.server is None:
        return
    elif message.content.startswith(command_trigger):
        await custom_command_check(message)
    elif message.content.lower() == 'witness me':
        await bot.send_message(message.channel, "WITNESSED")
    elif message.content.lower() == 'cut my life':
        await bot.send_message(message.channel, "INTO PIECES")
        await asyncio.sleep(3)
        await bot.send_message(message.channel, "THIS IS MY LAST RESORT")
    elif message.content.lower() == 'damn':
        await bot.send_message(message.channel, "daniel")
    elif message.content.lower().find('vmboys') != -1:
        if random.randint(0, 1) == 0:
            await bot.send_message(message.channel, "_WHEEZE_")
        else:
            await bot.send_message(message.channel, "haha, nice")

    await bot.process_commands(message)


async def custom_command_check(message):
    # TODO: image search support
    # TODO: gambling & games
    query = message.content[1:]
    cur.execute("SELECT * FROM message_commands WHERE invoke = (%s)", [query])
    # command_details = c_commands.get(query[0])
    try:
        invoke, to_send, is_tts, idk = cur.fetchone()
    except TypeError:
        return

    await bot.send_typing(message.channel)
    """ add custom message commands here """
    await bot.send_message(message.channel, to_send, tts=is_tts)
    # if arguments[0] == 'voice':
    #     await voice_command(arguments, message)

async def create_server_dirs():
    for server in bot.servers:
        if not os.path.exists('data/' + server.name + ' - ' + server.id):
            os.mkdir('data/' + server.name + ' - ' + server.id)


@bot.event
async def on_server_join(server):
    if not os.path.exists('data/' + server.name + ' - ' + server.id):
        os.mkdir('data/' + server.name + ' - ' + server.id)


@bot.event
async def on_ready():
    print('logged in as: ' + bot.user.name)
    print('bot id: ' + bot.user.id)
    await create_server_dirs()


if __name__ == '__main__':
    bot.add_cog(general.General(bot))
    bot.add_cog(voice.Voice(bot))
    bot.add_cog(games.Games(bot))
    bot.run(str(os.environ['DISCORD_TOKEN']))

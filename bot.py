# import discord
from discord.ext import commands
import asyncio
import random
import configparser
from cogs import general, games
import os


config = configparser.ConfigParser()
config.read('config')
# bot_token = config['discord']['BotToken']
command_trigger = config['messages']['commandTrigger']

# Bot vars
prefixes = ['`', '?']
description = '''
fun entertainment
'''
# help_attrs = dict()
bot = commands.Bot(command_prefix=prefixes, description=description)

# General global vars
c_commands = {}


# gross stuff from before
def populate_from_files():
    with open('data/commandlist.txt', encoding='UTF-8') as f:
        cur_line = ""
        for line in f:
            cur_line += line
            # print(curStr)
            if cur_line.endswith("|%\n"):
                firstSpace = cur_line.index(" ")
                word = cur_line[0:firstSpace]
                stuff = cur_line[firstSpace + 1:]
                c_commands[word] = stuff
                cur_line = ""


@bot.event
async def on_message(message):
    # handles custom commands first
    # if message.author.id == client.user.id:
    #     return
    if message.content == '' or message.server is None:
        return
    elif message.content.startswith(command_trigger):
        await command_check(message)
    elif message.content == 'WITNESS ME':
        await bot.send_message(message.channel, "WITNESSED")
    elif message.content == 'cut my life':
        await bot.send_message(message.channel, "INTO PIECES")
        await asyncio.sleep(3)
        await bot.send_message(message.channel, "THIS IS MY LAST RESORT")

    await bot.process_commands(message)


async def command_check(message):
    # TODO: image search support
    # TODO: gambling & games
    query = message.content[1:].split()
    command_details = c_commands.get(query[0])

    if command_details is None:
        return
    else:
        arguments = []
        '''        # cool programming ahead:
        firstComma = command_details[0].index(",")
        secondComma = command_details[0].index(",", firstComma + 1)
        beginPhrase = command_details[0].index("%|")
        endPhrase = command_details[0].index("%|", beginPhrase + 2)
        thirdComma = command_details[0].index(",", endPhrase + 2)
        fourthComma = command_details[0].index(",", thirdComma + 1)
        try:
            fifthComma = command_details[0].index(",", fourthComma + 1)
        except ValueError:
            fifthComma = len(command_details[0])
        arguments.append(command_details[0][:firstComma])
        arguments.append(command_details[0][beginPhrase + 2:endPhrase])
        arguments.append(command_details[0][thirdComma + 1:fourthComma])
        arguments.append(command_details[0][fourthComma + 1:fifthComma])
        '''
        s1, s2 = command_details.split(',', 1)
        phrase = s2.split('%|', 2)
        remains = phrase[2].split(',')
        arguments.extend([s1, phrase[1]])
        arguments.extend(remains[1:])

        if arguments[0] == 'message':
            await bot.send_typing(message.channel)
            """ add custom message commands here """
            if arguments[2] == "true":
                await bot.send_message(message.channel, arguments[1], tts=True)
            else:
                await bot.send_message(message.channel, arguments[1])
        # if arguments[0] == 'voice':
            # await voice_command(arguments, message)


@bot.event
async def on_ready():
    print('logged in as: ' + bot.user.name)
    print('bot id: ' + bot.user.id)
    populate_from_files()


if __name__ == '__main__':
    bot.add_cog(games.Games(bot))
    bot.add_cog(general.General(bot))
    bot.run(str(os.environ['DISCORD_TOKEN']))

import discord
from discord.ext import commands
import asyncio
import random
import configparser
from cogs import tests

config = configparser.ConfigParser()
config.read('config')
bot_token = config['discord']['BotToken']

prefixes = ['`', '?']
description = '''
fun entertainment
'''
# help_attrs = dict()
bot = commands.Bot(command_prefix=prefixes, description=description)


@bot.command(name='hi', aliases=['hello', 'hey'], pass_context=True)
async def greeting(ctx):
    """Greets the bot"""
    print('ok')
    await bot.say('hello {0.name}'.format(ctx.message.author))


@bot.command()
async def roll(dice: str='1d6'):
    """Rolls a dice in NdN format.
    (fully copied from the samples hahahahahah)"""
    try:
        rolls, limit = map(int, dice.split('d'))
    except Exception:
        await bot.say('Format has to be in NdN!')
        return

    result = ', '.join(str(random.randint(1, limit)) for r in range(rolls))
    await bot.say(result)


@bot.event
async def on_ready():
    print('logged in as: ' + bot.user.name)
    print('bot id: ' + bot.user.id)

if __name__ == '__main__':
    bot.add_cog(tests.Games(bot))
    bot.run(bot_token)

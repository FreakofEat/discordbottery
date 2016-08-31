from discord.ext import commands
import random
import psycopg2
import urllib.parse

class Games:
    """bot games (NOT WORKING YET)
    (B) = Can bet on
    Bet by starting your command with the bet command
    (e.g '`bet 4 flip h' to bet 4 currency that you'll get heads)"""

    def __init__(self, bot: commands.Bot, conn):
        self.bot = bot
        self.conn = conn
        # self.database = urllib.parse.

    @commands.command()
    async def play(self):
        await self.bot.say('i dont know how to')

    @commands.command()
    async def roll(self, dice: str = '1d6'):
        """Rolls a dice in NdN format.
        (fully copied from the samples hahahahahah)"""
        try:
            rolls, limit = map(int, dice.split('d'))
        except Exception:
            await self.bot.say('Format has to be in NdN!')
            return

        result = ', '.join(str(random.randint(1, limit)) for r in range(rolls))
        await self.bot.say(result)

    # TODO: Finish bet command
    '''
    @commands.command(pass_context=True)
    async def bet(self, ctx):
        """This doesnt work yet so dont even try"""
        try:
            invoke, curr, command = ctx.message.split(" ", 2)
            self.bot.get_command(command)
            self.bot.process_commands
        except:
            await self.bot.say('what are you saying')
    '''

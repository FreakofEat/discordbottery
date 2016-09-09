from discord.ext import commands
import random
import psycopg2
import urllib.parse


# TODO: gambling & games
class Games:
    """bot games (NOT WORKING YET)
    (B) = Can bet on
    Bet by adding '$(number)' to the end of a game
    (e.g '`flip h $3' to bet 3 currency that you'll get heads)"""

    def __init__(self, bot: commands.Bot, conn):
        self.bot = bot
        self.conn = conn
        # self.database = urllib.parse.

    @commands.command()
    async def play(self):
        await self.bot.say('i dont know how to')

    @commands.command(pass_context=True)
    async def roll(self, ctx):
        """Rolls a dice in NdN format.
        (fully copied from the samples hahahahahah)"""
        # TODO: fix this
        split = ctx.message.content.split()
        if len(split) == 1:
            dice = '1d6'
        else:
            dice = split[1]
        try:
            rolls, limit = map(int, dice.split('d'))
        except Exception:
            await self.bot.say('Format has to be in NdN!')
            return

        result = ', '.join(str(random.randint(1, limit)) for r in range(rolls))
        await self.bot.say(result)

    @commands.command(pass_context=True)
    async def flip(self, ctx):
        print('ok')

    @commands.command(pass_context=True)
    async def bank(self, ctx):
        cur = self.conn.cursor()
        cur.execute("SELECT currency FROM bank WHERE user_id = (%s)",
                    [ctx.message.author.id])
        currency = str(cur.fetchone())
        self.bot.say(currency)
        cur.close()

    # TODO: Finish bet command

    @commands.command(pass_context=True)
    async def bet(self, ctx):
        """This doesnt work yet so dont even try"""
        try:
            invoke, curr, command = ctx.message.split(" ", 2)
            self.bot.get_command(command)
            #self.bot.process_commands
        except:
            await self.bot.say('what are you saying')
        finally:
            return



def bet_check(message):
    print('ok')
    return True

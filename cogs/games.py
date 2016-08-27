from discord.ext import commands
import random

class Games:
    """bot games"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.leaderboards = None

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

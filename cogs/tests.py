from discord.ext import commands


class Games:
    """bot games"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.leaderboards = None

    @commands.command()
    async def play(self):
        await self.bot.say('i dont know how to')

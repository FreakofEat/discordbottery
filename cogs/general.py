from discord.ext import commands

# global vars

class General:
    """general bot commands!!!!"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='hi', aliases=['hello', 'hey'], pass_context=True)
    async def greeting(self, ctx):
        """Says hi to the bot in its native tongue"""
        await self.bot.say('hello {0.name}'.format(ctx.message.author))

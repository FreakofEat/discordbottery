from discord.ext import commands
import json
import aiohttp
import os

class General:
    """general bot commands!!!!"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='hi', aliases=['hello', 'hey'], pass_context=True)
    async def greeting(self, ctx):
        """Says hi to the bot in its native tongue"""
        await self.bot.say('hello {0.name}'.format(ctx.message.author))

    @commands.command(aliases=['i', 'img'], pass_context=True)
    async def image(self, ctx):
        """Searches for an image on bing
        5000 searches a month so dkm (m=my search abilities)"""
        query = ctx.message.content.split(" ", 1)
        if len(query) == 1:
            await self.bot.say(
                'why dont you actually search for something ? Hm?')
            return

        base_url = 'https://api.datamarket.azure.com/Bing/Search/v1/Composite?Sources=%27image%27'
        search_q = '%27' + query[1].replace(' ', '+') + '%27'
        url = base_url + '&Query=' + search_q + '&$top=1&$format=JSON'

        session = aiohttp.ClientSession()
        async with session.get(
                url, auth=("", os.environ['BING_API_KEY'])) as response:
            results = await response.json()
            response.close()
        session.close()

        image_url = results['d']['results'][0]['Image'][0]['MediaUrl']
        await self.bot.say(image_url)


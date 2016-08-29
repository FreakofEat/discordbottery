from discord.ext import commands
import aiohttp
import os

class General:
    """general bot commands!!!!"""
    # TODO: 'define' command
    # TODO: 'translate' command

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

        num_test = query[1].rsplit(" ", 1)
        try:
            offset = int(num_test[1])-1
            query[1] = num_test[0]
        except:
            offset = 0

        image_url = await bing_img_search(query[1], offset=offset)
        await self.bot.say(image_url)

    @commands.command(name='imagea', aliases=['ia', 'imga'], pass_context=True)
    async def _image_not_safe(self, ctx):
        """image, no filter. discord keeps logs fyi
        5000 searches a month so dkm (m=my search abilities)"""
        query = ctx.message.content.split(" ", 1)
        if len(query) == 1:
            await self.bot.say(
                'why dont you actually search for something ? Hm?')
            return

        num_test = query[1].rsplit(" ", 1)
        try:
            offset = int(num_test[1])-1
            query[1] = num_test[0]
        except:
            offset = 0

        image_url = await bing_img_search(query[1], safe=False, offset=offset)
        await self.bot.say(image_url)


async def bing_img_search(query, safe=True, offset=0):
    base_url = 'https://api.datamarket.azure.com/Bing/Search/v1/Composite?Sources=%27image%27'
    search_q = '%27' + query.replace(' ', '+') + '%27'
    if not safe:
        search_q += '&Adult=%27Off%27'
    url = base_url + '&Query=' + search_q + \
        '&$top=1&$format=JSON&$skip=' + str(offset)

    session = aiohttp.ClientSession()
    async with session.get(
            url, auth=("", os.environ['BING_API_KEY'])) as response:
        results = await response.json()
        response.close()
    session.close()

    image_url = results['d']['results'][0]['Image']
    if len(image_url) > 0:
        image_url = image_url[0]['MediaUrl']
    else:
        image_url = "No results"
    return image_url

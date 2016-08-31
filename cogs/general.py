from discord.ext import commands
import aiohttp
import os
import asyncio
import random
import urllib.parse
from selenium import webdriver
from bs4 import BeautifulSoup
import threading

# global vars
js_driver = None

class General:
    """general bot commands!!!!"""
    # TODO: 'define' command
    # TODO: 'translate' command
    # TODO: 'grammar' command (after the deadline api)

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

        search_urlsafe = urllib.parse.quote_plus(query[1])
        image_url = await bing_img_search(search_urlsafe, offset=offset)
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

        search_urlsafe = urllib.parse.quote_plus(query[1])
        image_url = await bing_img_search(search_urlsafe,
                                          safe=False, offset=offset)
        await self.bot.say(image_url)

    @commands.command()
    async def copypasta(self, search=""):
        """Pastes a random copypasta (copypasterino.me)
        add a query after to search"""
        pasta = ""
        if search != "":
            search_urlsafe = urllib.parse.quote_plus(search)
            url = 'http://copypasterino.me/search/' + search_urlsafe
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as r:
                    json = await r.json()
                    pasta = json[random.randrange(0, len(json))]['pasta']
        else:
            url = 'http://copypasterino.me/static/all/hot/' + \
                  str(random.randint(1, 7))
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as r:
                    json = await r.json()
                    pasta = json[random.randrange(0, len(json))]['pasta']
        """
        url = 'http://copypasterino.me/general/hot/' + str(random.randint(1, 7))
        # print(url)
        html = await get_html_js(url)
        if html is None:
            return
        soup = BeautifulSoup(html, 'html.parser')
        pastas = soup.find_all(class_='well col-md-6 col-sm-8 col-xs-10')
        rand_p = random.randrange(0, len(pastas))
        p_soup = BeautifulSoup(str(pastas[rand_p]), 'html.parser')
        text = p_soup.get_text()
        pasta = text.split("Tags: #", 1)[0]
        # print('full pasta = ' + pasta)
        """
        while len(pasta) > 0:
            if len(pasta) >= 2000:
                part = pasta[0:1999]
                await self.bot.say(part)
                pasta = pasta[1999:]
                # print('pasta = ' + pasta)
            else:
                await self.bot.say(pasta)
                # print('done')
                return


class _GetHtmlJs(threading.Thread):
    def __init__(self, driver, url):
        threading.Thread.__init__(self)
        self.driver = driver
        self.url = url
        self.html = ""

    def run(self):
        self.driver.get(self.url)
        # print('gotten')
        self.html = self.driver.page_source

async def get_html_js(url):
    print('start')
    global js_driver
    if js_driver is None:
        js_driver = "starting"
        try:
            js_driver = webdriver.PhantomJS(str(os.environ['PHANTOM_JS']))
        except:
            js_driver = None
        print('driver')
    while js_driver == "starting":
        # print('waiting js_driver')
        await asyncio.sleep(5)
    if js_driver is None:
        return
    html_thread = _GetHtmlJs(js_driver, url)
    html_thread.start()
    time_count = 0
    while html_thread.is_alive():
        if time_count > 10:
            print('timecount done')
            return None
        await asyncio.sleep(1)
        html_thread.join(0.1)
        time_count += 1
        # print('timecount++')
    return html_thread.html


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

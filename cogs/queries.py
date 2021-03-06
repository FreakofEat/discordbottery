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
session = aiohttp.ClientSession()


class Queries:
    """commands that return info of sorts!!!"""
    # TODO: 'define' command
    # TODO: 'translate' command

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(aliases=['i', 'img'], pass_context=True)
    async def image(self, ctx):
        """Searches for an image on bing
        5000 searches a month so dkm (m=my search abilities)"""
        query = ctx.message.content.split(" ", 1)
        if len(query) == 1:
            await self.bot.say(
                'why dont you actually search for something ? Hm?')
            return
        # Checks if message has a number at the end (the index to return)
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
        """image, #nofilter. discord keeps logs fyi
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

    # Webscraping
    '''
    @commands.command()
    async def copypasta(self, search=""):
        """Pastes a random copypasta (copypasterino.me)
        add a query after to search"""
        pasta = ""
        if search != "":
            search_urlsafe = urllib.parse.quote_plus(search)
            url = 'http://copypasterino.me/search/' + search_urlsafe
            async with session.get(url) as r:
                json = await r.json(encoding='utf-8')
                pasta = json[random.randrange(0, len(json))]['pasta']
        else:
            url = 'http://copypasterino.me/static/all/hot/' + \
                  str(random.randint(1, 7))
            async with session.get(url) as r:
                json = await r.json(encoding='utf-8')
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
    '''
                
    @commands.command(pass_context=True)
    async def grammar(self, ctx):
        """checks for grammatical errors"""
        try:
            query = ctx.message.content.split(" ", 1)[1]
        except IndexError:
            return
        if len(query) == 0:
            return
        output = await after_the_deadline(query)
        if output == "":
            await self.bot.say('no problems found!')
        else:
            await self.bot.say(output)

    @commands.command(pass_context=True)
    async def spelling(self, ctx):
        """checks for spelling errors AND grammatical errors!"""
        try:
            query = ctx.message.content.split(" ", 1)[1]
        except IndexError:
            return
        if len(query) == 0:
            return
        output = await after_the_deadline(query, type=1)
        if output == "":
            await self.bot.say('no problems found!')
        else:
            await self.bot.say(output)

    @commands.command()
    async def define(self, word: str="define", *args):
        url = 'http://api.pearson.com/v2/dictionaries/laad3/entries?search=' + word
        async with session.get(url) as r:
            response = await r.json(encoding='utf-8')
        print('test')
        #output = ""


class _GetHtmlJs(threading.Thread):
    """ used by get_html_js """
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
    """ get html from websites using ghostdriver
    (bypasses some browser checks) """
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
    """doesn't work anymore"""
    return None
    base_url = 'https://api.datamarket.azure.com/Bing/Search/v1/Composite?Sources=%27image%27'
    search_q = '%27' + query.replace(' ', '+') + '%27'
    if not safe:
        search_q += '&Adult=%27Off%27'
    url = base_url + '&Query=' + search_q + \
        '&$top=1&$format=JSON&$skip=' + str(offset)

    async with session.get(
            url, auth=("", os.environ['BING_API_KEY'])) as response:
        results = await response.json()
        response.close()

    image_url = results['d']['results'][0]['Image']
    if len(image_url) > 0:
        image_url = image_url[0]['MediaUrl']
    else:
        image_url = "No results"
    return image_url

async def after_the_deadline(query, type=0):
    # type=0: grammar only
    # type=1: spelling too!!
    api_key = random.getrandbits(32)
    data = {'key': str(api_key), 'data': query}
    if type == 0:
        url = 'http://service.afterthedeadline.com/checkGrammar'
    else:
        url = 'http://service.afterthedeadline.com/checkDocument'
    async with session.post(url, data=data) as r:
        response = await r.text()
    soup = BeautifulSoup(response, 'html.parser')
    output = ""
    found_errors = []
    for error in soup.find_all('error'):
        error_text = error.find('string')
        if error_text not in found_errors:
            output += 'Found: "' + error.find('string').text + '". '
            found_errors.append(error_text)
            suggestions = ""
            suggests = error.find_all('option')
            for suggest in error.find_all('option'):
                suggestions += "/" + suggest.text
            if suggestions == "":
                suggestions = " No suggestions"
            output += error.find('description').text + \
                ": " + suggestions[1:] + "\n"
    return output


def close_aiohttp():
    session.close()

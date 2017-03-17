from discord.ext import commands
from cogs import queries
import aiohttp
import asyncio
import random
import time

# global vars
session = aiohttp.ClientSession()

class Tasks:
    """auto"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def zooboys(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed:
            cur_time = time.localtime()
            if cur_time.tm_hour == 17 and cur_time.tm_min == 48:
                await self.bot.send_message(self.bot.get_channel('144849743368028160'),
                                            chr(random.randint(97, 122))) # Random letter
            await asyncio.sleep(60)

    async def who_up(self):
        await self.bot.wait_until_ready()
        who_up_words = ['NOTION', 'NUTRIENT', 'SAD', ':clown::clown::clown:',
                        'NEIGHBOUR', 'WILD', 'THOT', 'DANIEL', 'NEUTRON', 'gnarls barkley',
                        'neutrino', 'nuremberg', 'sour', 'power!', 'coward', 'flower',
                        'idiot', 'useless']
        who_up_min = random.randint(27, 59)
        who_up_hour = 5
        while not self.bot.is_closed:
            cur_time = time.localtime()
            if cur_time.tm_hour == who_up_hour and cur_time.tm_min == who_up_min:
                who_up_word = random.randint(0, len(who_up_words) - 1)
                await self.bot.send_message(self.bot.get_channel(
                    '144849743368028160'),
                    "IT'S REAL {} HOURS".format(who_up_words[who_up_word]))
                await asyncio.sleep(1)
                await self.bot.send_message(self.bot.get_channel(
                    '144849743368028160'), "WHO UP")


                res = 'first'
                while res is not None:
                    res = await self.bot.wait_for_message(
                        timeout=180,
                        channel=self.bot.get_channel('144849743368028160'))
                    image_url = await queries.bing_img_search(
                        'real nigga hours', safe=False,
                        offset=random.randint(0, 100))
                    async with session.get(image_url) as r:
                        file_name = image_url.rsplit('/', 1)[1]
                        file = await r.read()
                        with open(file_name, 'wb') as f:
                            f.write(file)
                        with open(file_name, 'rb') as f:
                            await self.bot.send_file(
                                self.bot.get_channel('144849743368028160'), f,
                                filename=file_name)
            await asyncio.sleep(59)

def close_aiohttp():
    session.close()

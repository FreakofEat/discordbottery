from discord.ext import commands
import aiohttp
import asyncio
import urllib.parse
from bs4 import BeautifulSoup
import threading

# global vars
session = aiohttp.ClientSession()


class Queries:
    """@botterypottery (dont @ me)"""
    # TODO: 'tweet' command
    # TODO: 'follow' command
    # TODO: 'retweet' command

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command()
    async def tweet(self, *, message:str=""):
        print('ok')

    def _generate_signature(self):
        print('ok')

    def _generate_header(self, consumer_key, nonce,
                         signature, timestamp, token):
        print('ok')

    def _percent_enc(self, string):
        return urllib.parse.quote(string, safe='')


def close_aiohttp():
    session.close()

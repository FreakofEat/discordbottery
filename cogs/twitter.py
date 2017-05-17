from discord.ext import commands
import aiohttp
import asyncio
import urllib.parse
from bs4 import BeautifulSoup
import os
import threading
import random
import base64
import time
import hmac
import hashlib

# global vars
session = aiohttp.ClientSession()


class Twitter:
    """@botterypottery (dont @ me)"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command()
    async def tweet(self, *, message: str=""):
        """tweet a message and more... (`help tweet for more...)
        d [username] [message] to dm
        @[username] [message] to mention (might not properly tag them, 
                                          try `reply otherwise)
        https://support.twitter.com/articles/14020 for more..."""
        if message == "":
            return
        elif len(message) > 140:
            await self.bot.say('a little long, dont you think')
            return

        url = 'https://api.twitter.com/1.1/statuses/update.json'
        t_params = self._generate_parameters()
        t_header = self._generate_header('post', url, t_params,
                                         status=message)
        #enc_msg = self._percent_enc(message)
        async with session.post(
                url, data={'status': message}, headers=t_header) as r:
            json = await r.json()
            if r.status != 200:
                await self.bot.say(json['errors'][0]['message'])
                return
            temp = 'Tweeted: {}\nhttps://twitter.com/botterypottery/status/{}'
            temp.format(message, json['id_str'])
            await self.bot.say(temp)

    @commands.command()
    async def follow(self, user: str = ""):
        """follow a user"""
        if user == "":
            return

        url = 'https://api.twitter.com/1.1/friendships/create.json'
        t_params = self._generate_parameters()
        t_header = self._generate_header('post', url, t_params,
                                         screen_name=user)
        # enc_msg = self._percent_enc(message)
        async with session.post(
                url, data={'screen_name': user}, headers=t_header) as r:
            json = await r.json()
            if r.status != 200:
                await self.bot.say(json['errors'][0]['message'])
                return
            await self.bot.say('followed ' + json['name'] + '(' +
                               'https://twitter.com/' + user + ')')

    @commands.command()
    async def unfollow(self, user: str = ""):
        """unfollow a user"""
        if user == "":
            return

        url = 'https://api.twitter.com/1.1/friendships/destroy.json'
        t_params = self._generate_parameters()
        t_header = self._generate_header('post', url, t_params,
                                         screen_name=user)
        # enc_msg = self._percent_enc(message)
        async with session.post(
                url, data={'screen_name': user}, headers=t_header) as r:
            json = await r.json()
            if r.status != 200:
                await self.bot.say(json['errors'][0]['message'])
                return
            await self.bot.say('unfollowed ' + json['name'] + '(' +
                               'https://twitter.com/' + user + ')')

    @commands.command()
    async def retweet(self, tweet: str = ""):
        """retweets a tweet given by id"""
        if tweet == "":
            return
        elif not tweet.isnumeric():
            split = tweet.split('/')
            rt = split[-1]
            if not rt.isnumeric():
                rt = split[-2]
        else:
            rt = tweet
        url = 'https://api.twitter.com/1.1/statuses/retweet/' + rt + '.json'
        t_params = self._generate_parameters()
        t_header = self._generate_header('post', url, t_params)
        # enc_msg = self._percent_enc(message)
        async with session.post(
                url, data={}, headers=t_header) as r:
            json = await r.json()
            if r.status != 200:
                await self.bot.say(json['errors'][0]['message'])
                return
            await self.bot.say('retweeted')

    @commands.command(name='deletetweet')
    async def _delete_tweet(self, tweet: str = ""):
        """deletes a tweet given by id"""
        if tweet == "":
            return
        elif not tweet.isnumeric():
            split = tweet.split('/')
            rt = split[-1]
            if not rt.isnumeric():
                rt = split[-2]
        else:
            rt = tweet
        url = 'https://api.twitter.com/1.1/statuses/destroy/' + rt + '.json'
        t_params = self._generate_parameters()
        t_header = self._generate_header('post', url, t_params)
        # enc_msg = self._percent_enc(message)
        async with session.post(
                url, data={}, headers=t_header) as r:
            json = await r.json()
            if r.status != 200:
                await self.bot.say(json['errors'][0]['message'])
                return
            await self.bot.say('deleted')

    @commands.command()
    async def reply(self, tweet: str = "", *, message: str = ""):
        """replies to a specific tweet id ((id) (@user) (message))"""
        if tweet == "":
            return
        elif not tweet.isnumeric():
            split = tweet.split('/')
            status_id = split[-1]
            if not status_id.isnumeric():
                status_id = split[-2]
        else:
            status_id = tweet

        if message == "":
            return
        elif len(message) > 140:
            await self.bot.say('a little long, dont you think')
            return

        url = 'https://api.twitter.com/1.1/statuses/update.json'
        t_params = self._generate_parameters()
        t_header = self._generate_header('post', url, t_params,
                                         status=message,
                                         in_reply_to_status_id=status_id)
        #enc_msg = self._percent_enc(message)
        async with session.post(
                url, data={'status': message,
                           'in_reply_to_status_id': status_id},
                headers=t_header) as r:
            json = await r.json()
            if r.status != 200:
                await self.bot.say(json['errors'][0]['message'])
                return
            await self.bot.say('https://twitter.com/botterypottery/status/' + \
                               json['id_str'])

    @commands.command()
    async def trends(self, *, message: str = ""):
        """lists worldwide or location based trends"""
        if message == "":
            woeid = 1
            output = 'trending worldwide'
        else:
            url = 'https://api.twitter.com/1.1/trends/available.json'
            t_params = self._generate_parameters()
            t_header = self._generate_header('get', url, t_params)
            async with session.get(
                    url, headers=t_header) as r:
                json = await r.json()
                if r.status != 200:
                    await self.bot.say(json['errors'][0]['message'])
                    return
                search_complete = False
                index = -1
                woeid = -1
                while not search_complete:
                    index += 1
                    if index >= len(json) - 1:
                        await self.bot.say('couldnt find that location')
                        return
                    elif index % 10 == 0:
                        await asyncio.sleep(0.01)
                    if json[index]['country'].lower() == message.lower():
                        search_complete = True
                        woeid = json[index]['woeid']
                    elif json[index]['name'].lower() == message.lower():
                        search_complete = True
                        woeid = json[index]['woeid']
                output = 'trends from ' + json[index]['country'] + \
                                   ', ' + json[index]['name']

        url = 'https://api.twitter.com/1.1/trends/place.json'
        t_params = self._generate_parameters()
        t_header = self._generate_header('get', url, t_params,
                                         id=str(woeid))
        # enc_msg = self._percent_enc(message)
        async with session.get(
                url, params=[('id', woeid)], headers=t_header) as r:
            json = await r.json()
            if r.status != 200:
                await self.bot.say(json['errors'][0]['message'])
                return
            for trend in json[0]['trends']:
                output += '\n"' + trend['name'] + '"'
                if trend['tweet_volume'] is not None:
                    output += ': ' + str(trend['tweet_volume']) + ' tweets'
            await self.bot.say(output)

    @commands.command()
    async def mentions(self):
        """last 20 tweets mentioning YOU"""
        # Not complete yet
        url = 'https://api.twitter.com/1.1/statuses/mentions_timeline.json'
        t_params = self._generate_parameters()
        t_header = self._generate_header('get', url, t_params)
        # enc_msg = self._percent_enc(message)
        async with session.get(
                url, headers=t_header) as r:
            json = await r.json()
            if r.status != 200:
                await self.bot.say(json['errors'][0]['message'])
                return
            '''
            output = ""
            for trend in json[0]['trends']:
                output += '\n"' + trend['name'] + '"'
                if trend['tweet_volume'] is not None:
                    output += ': ' + str(trend['tweet_volume']) + ' tweets'
            await self.bot.say(output)
            '''

    def _generate_signature(self, method, url, parameters):
        """ Generates the OAuth signature (some research required) """
        enc_parameters = {}
        for key in parameters:
            enc_key = self._percent_enc(key)
            enc_val = self._percent_enc(parameters[key])
            enc_parameters[enc_key] = enc_val
        p_str = ""
        for key in sorted(enc_parameters):
            p_str += key + '=' + enc_parameters[key] + '&'
        p_str = p_str[0:-1]
        base_str = method.upper() + '&' + self._percent_enc(url) + '&'
        base_str += self._percent_enc(p_str)
        s_key = self._percent_enc(str(os.environ['TWITTER_CONSUMER_SECRET']))
        s_key += '&'
        s_key += self._percent_enc(str(os.environ['TWITTER_TOKEN_SECRET']))
        base_str = base_str.encode()
        s_key = s_key.encode()
        t_hash = hmac.new(s_key, base_str, digestmod=hashlib.sha1)
        digest = t_hash.digest()
        sig = base64.b64encode(digest)
        return sig.decode()

    def _generate_header(self, method, url, parameters, **kwargs):
        """ add url parameters to kwargs """
        sig_parameters = {}
        for key in parameters:
            sig_parameters[key] = parameters[key]
        for key in kwargs:
            sig_parameters[key] = kwargs[key]
        parameters['oauth_signature'] = self._generate_signature(
            method, url, sig_parameters)

        enc_params = {}
        for key in parameters:
            enc_key = self._percent_enc(key)
            enc_val = self._percent_enc(parameters[key])
            enc_params[enc_key] = enc_val
        oauth_string = 'OAuth '
        for key in enc_params:
            oauth_string += key + '="' + enc_params[key] + '", '
        header = {'Authorization': oauth_string[0:-2]}
        return header

    def _generate_parameters(self, **kwargs):
        """ add extra oauth parameters to kwargs """
        params = {'oauth_consumer_key': str(os.environ['TWITTER_CONSUMER']),
                  'oauth_token': str(os.environ['TWITTER_TOKEN']),
                  'oauth_signature_method': 'HMAC-SHA1',
                  'oauth_version': '1.0'}
        for key in kwargs:
            params[key] = kwargs[key]
        nonce = ''.join([str(random.randint(0, 9)) for i in range(16)])
        params['oauth_nonce'] = nonce
        params['oauth_timestamp'] = str(int(time.time()))
        return params

    def _percent_enc(self, string):
        return urllib.parse.quote(string, safe='')


def close_aiohttp():
    session.close()

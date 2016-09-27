from discord.ext import commands
import random
import os
import markovify
import re

class Markov:
    """markov with https://github.com/jsvine/markovify
    thanks buzzfeed"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(pass_context=True)
    async def markov(self, ctx, user="", *, seed: str=""):
        """markov sentence MAKER. will occasionally fail with no output
        `markov [user] [seed]
        `markov without a user picks a random user
        seed must be exactly 2 words"""
        server = ctx.message.server
        directory = 'data/' + server.name + ' - ' + server.id + '/Markov/'
        file_list = []
        for entry in os.scandir(directory):
            if entry.is_file() and entry.name.endswith('.json'):
                file_list.append(entry.name)
        if user == "":
            file = file_list[random.randrange(0, stop=len(file_list))]
            user = file[0:-5]
            for member in server.members:
                if member.id == user:
                    user = member.name
        else:
            file = ""
            for member in server.members:
                if member.name == user or member.id == user:
                    file = member.id + '.json'
                    user = member.name
            if file == "":
                await self.bot.say('couldnt find that user')
                return
        file = file[0:-5]  # minus .json
        print(user)
        with open(directory + file, mode='r',
                  encoding='utf-8') as f:
            text = f.read()
        #chain = markovify.Chain.from_json(text)
        #text_model = markovify.Text.from_chain(text)
        text_model = MyMarkov(text)  # make markov each time
        print("markov'd")
        output = None
        attempts = 0
        if seed == "":
            while output is None and attempts < 15:
                attempts += 1
                if attempts < 8:
                    output = text_model.make_sentence(tries=4)
                else:
                    print('try harder')
                    output = text_model.make_sentence(
                        max_overlap_ratio=1, max_overlap_total=15, tries=5)
        else:
            while output is None and attempts < 15:
                attempts += 1
                if attempts < 8:
                    output = text_model.make_sentence_with_start(seed, tries=3)
                else:
                    print('try harder')
                    output = text_model.make_sentence_with_start(
                        seed, max_overlap_ratio=1,
                        max_overlap_total=15, tries=5)
        if output is not None:
            await self.bot.say(user + ": " + output)
        else:
            print('markovnfail')

    def _get_random_markov_file(self, server):
        directory = 'data/' + server.name + ' - ' + server.id + '/Markov/'
        file_list = []
        for entry in os.scandir(directory):
            if entry.is_file() and entry.name.endswith('.json'):
                file_list.append(entry.name)
        file = file_list[random.randrange(0, stop=len(file_list))]
        user = file[0:-5]
        for member in server.members:
            if member.id == user:
                user = member.name
        return (user, file)

    @commands.command(name='log', pass_context=True)
    async def _get_logs(self, ctx):
        """dont use this or the bot will be unusable for like 30 mins"""
        for server in self.bot.servers:
            directory = 'data/' + server.name + ' - ' + server.id + '/Markov'
            if not os.path.exists(directory):
                os.mkdir(directory)
            directory += '/'
            print(directory)
            users = dict()
            for channel in server.channels:
                async for message in self.bot.logs_from(channel, limit=100000):
                    if message.author.id in users.keys():
                        users[message.author.id] += message.content + '\n'
                    else:
                        users[message.author.id] = message.content + '\n'
            for key in users.keys():
                with open(directory + key, mode='w', encoding='utf-8') as file:
                    file.write(users[key])
        print('donelogs')

    @commands.command(name='genMarkov', pass_context=True)
    async def _generate_markov(self, ctx):
        """dont use this or the bot will be unusuable for like 30 mins"""
        for server in self.bot.servers:
            directory = 'data/' + server.name + ' - ' + server.id + '/Markov/'
            for root, dirs, files in os.walk(directory):
                for file in files:
                    if not file.endswith('.json'):
                        with open(directory + file, mode='r',
                                  encoding='utf-8') as f:
                            text = f.read()
                        text_model = markovify.NewlineText(text)
                        with open(directory + file + '.json', mode='w',
                                  encoding='utf-8') as f:
                            f.write(text_model.chain.to_json())
        print('donemarkovifys')

class MyMarkov(markovify.NewlineText):
    """overrides to enable emojis and dumb punctuation"""

    def word_split(self, sentence):
        """
        include unicode
        """
        word_split_pattern = re.compile('\s+', flags=re.U)
        return re.split(word_split_pattern, sentence)

    def test_sentence_input(self, sentence):
        """
        no filter hahahahahaha
        """
        return True

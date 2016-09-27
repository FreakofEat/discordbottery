from discord.ext import commands
import random
import os
import markovify

class Markov:
    """markov with https://github.com/jsvine/markovify
    thanks buzzfeed"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(pass_context=True)
    async def markov(self, ctx, user="", *, seed: str=""):
        """markov sentence MAKER.
        `markov [user] [seed]
        `markov without a user picks a random user"""
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
            if file == "":
                await self.bot.say('couldnt find that user')
                return
        with open(directory + file, mode='r',
                  encoding='utf-8') as f:
            text = f.read()
        #chain = markovify.Chain.from_json(text)
        text_model = markovify.Text.from_chain(text)
        if seed == "":
            output = text_model.make_sentence(max_overlap_ratio=0.1,
                                              max_overlap_total=2)
            if output is not None:
                await self.bot.say(text_model.make_sentence())
        else:
            output = text_model.make_sentence_with_start(seed)
            if output is not None:
                await self.bot.say(text_model.make_sentence())

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

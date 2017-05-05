from discord.ext import commands
import discord.channel
import psycopg2
import random
import urllib.parse
import os
import asyncio
import base64


class General:
    """general bot commands!!!!"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Connects to database to be able to store new commands from `add
        urllib.parse.uses_netloc.append("postgres")
        url = urllib.parse.urlparse(str(os.environ["DATABASE_URL"]))
        self.conn = psycopg2.connect(
            database=url.path[1:],
            user=url.username, password=url.password,
            host=url.hostname, port=url.port
        )
        self.spoilers = dict()

    @commands.command(name='hi', aliases=['hello', 'hey'], pass_context=True)
    async def greeting(self, ctx):
        """Says hi to the bot in its native tongue"""
        await self.bot.say('hello {0.name}'.format(ctx.message.author))

    @commands.command(name='add')
    async def _add_command(self, cmd_type, cmd_trigger, *, cmd: str):
        """add a custom message command invoked by '!'!!!
        (`add [type] [trigger] [message])
        [type] can be 'message' or 'tts'
        [trigger] has to be one word
        """
        if cmd_type == 'tts':
            is_tts = True
        else:
            is_tts = False
        cur = self.conn.cursor()
        # Postgres query
        cur.execute( 
            "INSERT INTO message_commands (invoke, message, istts, idk)"
            " VALUES (%s, %s, %s, %s) "
            "ON CONFLICT (invoke) "
            "DO UPDATE SET message = EXCLUDED.message",
            [cmd_trigger, cmd, is_tts, True])
        self.conn.commit()
        cur.close()

    @commands.command(name='list')
    async def _list_commands(self):
        """lists all custom commands"""
        message_cmds = "regular commands:\n"
        tts_cmds = "tts commands:\n"
        cur = self.conn.cursor()
        cur.execute(
            "SELECT invoke FROM message_commands WHERE istts is true;")
        cmd_invokes = cur.fetchall()
        for invoke in cmd_invokes:
            tts_cmds += invoke[0] + ', '
        tts_cmds = tts_cmds[0:-2]
        cur.execute(
            "SELECT invoke FROM message_commands WHERE istts is false;")
        cmd_invokes = cur.fetchall()
        for invoke in cmd_invokes:
            message_cmds += invoke[0] + ', '
        message_cmds = message_cmds[0:-2]
        cur.close()
        await self.bot.say(message_cmds)
        await self.bot.say(tts_cmds)

    @commands.command()
    async def me(self):
        """look at me"""
        await self.bot.say('https://github.com/oyisre/discordbottery')

    @commands.command(pass_context=True)
    async def spoiler(self, ctx, *, message: str):
        """hides a spoiler message
        `spoiler [topic:] (spoiler message)
        the bot needs a role with 'manage messages' for speedy spoiler removal!!!
        if your spoiler has a ':' in it, make sure you add a topic or else you'll be sorry"""
        await self.bot.delete_message(ctx.message)
        if message.find(':') == -1:
            spoiler_topic = 'general'
        else:
            split = message.split(':')
            spoiler_topic = split[0]
            message = split[1]
        msgenc = base64.b64encode(message.encode())
        await self.bot.say(spoiler_topic + ' spoiler: ' + msgenc.decode())

    @commands.command(pass_context=True)
    async def reveal(self, ctx, code: str):
        """reveals a spoiler message from a given code
        only works in a one on one chat"""
        if type(ctx.message.channel) == discord.PrivateChannel:
            print('ok')
            msg = base64.b64decode(code.encode()).decode()
            await self.bot.say(msg)
        else:
            await self.bot.say('some privacy PLEASE')

from discord.ext import commands
import psycopg2
import urllib.parse
import os


class General:
    """general bot commands!!!!"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        urllib.parse.uses_netloc.append("postgres")
        url = urllib.parse.urlparse(str(os.environ["DATABASE_URL"]))
        self.conn = psycopg2.connect(
            database=url.path[1:],
            user=url.username, password=url.password,
            host=url.hostname, port=url.port
        )

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
        cur.execute(
            "INSERT INTO message_commands (invoke, message, istts, idk) VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
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
        await self.bot.say('https://github.com/FreakofEat/discordbottery')

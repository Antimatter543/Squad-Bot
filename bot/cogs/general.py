# general.py

import discord
from discord import app_commands
from discord.ext import commands

from random import choice, randint


class general(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.log = bot.log
        self.sLog = {}

    # Commands
    @commands.hybrid_command(
        name="ping",
        aliases=["p"],
        brief="Pong!, latency test",
        description="Sends Pong!, followed by the result of a latecny test",
        with_app_command=True,
    )
    @app_commands.guilds(discord.Object(id=809997432011882516))
    async def ping(self, ctx):
        await ctx.reply(f"Pong! {round(self.bot.latency * 1000)}ms", ephemeral=True)

    @commands.hybrid_command(
        name="fortune",
        aliases=["8ball", "predictions", "shake", "magic_ball"],
        brief="Shake a magic 8 ball",
        description="Get a fortune from the magic 8 ball",
        with_app_command=True,
    )
    @app_commands.describe(message="What do you wish to ask?")
    @app_commands.guilds(discord.Object(id=809997432011882516))
    async def magic_ball(self, ctx, *, message=""):
        options = [
            "It is certain.",
            "It is decidedly so.",
            "Without a doubt.",
            "Yes definitely.",
            "You may rely on it.",
            "As I see it, yes.",
            "Most likely.",
            "Outlook good.",
            "Yes.",
            "Signs point to yes.",
            "Reply hazy, try again.",
            "Ask again later.",
            "Better not tell you now.",
            "Cannot predict now.",
            "Concentrate and ask again.",
            "Don't count on it.",
            "My reply is no.",
            "My sources say no.",
            "Outlook not so good.",
            "Very doubtful.",
        ]
        if message != "":
            content = f"> {message}\n"
        else:
            content = ""
        await ctx.reply(content + choice(options))

    @commands.hybrid_command(
        name="6roll",
        aliases=["roll_dice", "dice"],
        brief="Roll a dice",
        description="Returns a random number between 1 and 6",
        with_app_command=True,
    )
    @app_commands.describe(sides="Number of sides.")
    @app_commands.guilds(discord.Object(id=809997432011882516))
    async def roll_dice(self, ctx, sides: int = 6):
        await ctx.send(f"Rolled a dice, it was a {randint(1,sides)}!")

    @commands.hybrid_command(name="hug", aliases=["love"], brief="", description="", with_app_command=True)
    @app_commands.guilds(discord.Object(id=809997432011882516))
    async def hug(self, ctx):
        await ctx.reply(":hugging:")

    @commands.command(
        name="decide",
        aliases=["d", "choose", "c"],
        brief="Chooses between a list of items",
        description="Returns a random value from a list of items given following the command",
    )
    @app_commands.guilds(discord.Object(id=809997432011882516))
    async def decide(self, ctx, *options):
        if len(options) == 0:
            return
        await ctx.reply(f'Options: [{"],[".join(options)}]\nSelected: {choice(options)}')

    @app_commands.command(
        name="decide", description="Returns a random value from a list of items given following the command"
    )
    @app_commands.guilds(discord.Object(id=809997432011882516))
    async def decide_slash(
        self,
        ctx,
        o0: str,
        o1: str = "",
        o2: str = "",
        o3: str = "",
        o4: str = "",
        o5: str = "",
        o6: str = "",
        o7: str = "",
        o8: str = "",
        o9: str = "",
    ):
        options = [o0, o1, o2, o3, o4, o5, o6, o7, o8, o9]
        options = [x for x in options if x != ""]
        await ctx.reply(f'Options: [{"],[".join(options)}]\nSelected: {choice(options)}')

    @commands.hybrid_command(
        name="clear",
        brief="Clears a number of your past messages",
        description="Clears a number of previous messages from a channel",
        with_app_command=True,
    )
    @app_commands.guilds(discord.Object(id=809997432011882516))
    @commands.is_owner()
    async def clear(self, ctx, amount=5):
        await ctx.channel.purge(limit=amount, before=ctx.message)


async def setup(bot):
    await bot.add_cog(general(bot))


async def teardown(bot):
    pass

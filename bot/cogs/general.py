# general.py

from random import choice, randint

import discord
from discord import app_commands
from discord.ext import commands


class general(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.log = bot.log

    # Commands
    @commands.hybrid_command(
        name="ping",
        aliases=["p"],
        brief="Pong!, latency test",
        description="Sends Pong!, followed by the result of a latecny test",
        with_app_command=True,
    )
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
    @app_commands.guilds(discord.Object(id=809997432011882516), discord.Object(id=676253010053300234))
    async def magic_ball(self, ctx: commands.Context, *, message=""):
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
        name="dice",
        aliases=["roll_dice", "6roll"],
        brief="Roll a dice",
        description="Returns a random number between 1 and 6",
        with_app_command=True,
    )
    @app_commands.describe(sides="Number of sides.")
    @app_commands.guilds(discord.Object(id=809997432011882516), discord.Object(id=676253010053300234))
    async def roll_dice(self, ctx: commands.Context, sides: int = 6):
        await ctx.send(f"Rolled a dice, it was a {randint(1,sides)}!")

    @commands.hybrid_command(name="hug", aliases=["love"], brief="", description="", with_app_command=True)
    @app_commands.guilds(discord.Object(id=809997432011882516), discord.Object(id=676253010053300234))
    async def hug(self, ctx):
        await ctx.reply(":hugging:")

    @commands.command(
        name="decide",
        aliases=["d", "choose", "c"],
        brief="Chooses between a list of items",
        description="Returns a random value from a list of items given following the command",
    )
    async def decide(self, ctx: commands.Context, *options):
        if len(options) == 0:
            return
        await ctx.reply(f'Options: [{"],[".join(options)}]\nSelected: {choice(options)}')


async def setup(bot):
    await bot.add_cog(general(bot))


async def teardown(bot):
    pass

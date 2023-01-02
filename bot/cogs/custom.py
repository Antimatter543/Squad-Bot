# custom.py
# The location for all additional or custom commands

from discord.ext import commands


class Custom(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.log = bot.log

    # Commands
    @commands.command(aliases=["sex2", "biggus dickus", "cock", "cum", "cumsum", "dick", "balls"], hidden=True)
    async def sex(self, ctx):
        logging.info(f"{ctx.author.name} ({ctx.author.nick}) called sex")
        if ctx.author.id not in self.sLog:
            self.sLog[ctx.author.id] = 0
        self.sLog[ctx.author.id] += 1
        if self.sLog[ctx.author.id] % 20 == 0:
            await ctx.send("https://i.redd.it/ofq6raed4ck71.jpg")
            return
        if self.sLog[ctx.author.id] % 50 == 0:
            await ctx.send(
                "https://preview.redd.it/uvvfzj73pae71.png?auto=webp&s=2ccf99549a0f445170e15e0227404d804d8052fb"
            )
            return
        options = [
            "I am an artificial being and can not satisfy you in this way.",
            "https://i.kym-cdn.com/entries/icons/original/000/033/758/Screen_Shot_2020-04-28_at_12.21.48_PM.png",
            "Nah, I mostly just lie there.",
            "With a human being? No. With myself? Most definitely.",
            "uWu",
        ]
        num = randint(0, 100)
        if num < 20:
            await ctx.send(options[0])
        elif num < 70:
            await ctx.send(options[1])
        elif num < 80:
            await ctx.send(options[2])
        elif num < 90:
            await ctx.send(options[3])
        else:
            await ctx.send(options[4])


async def setup(bot):
    await bot.add_cog(Custom(bot))

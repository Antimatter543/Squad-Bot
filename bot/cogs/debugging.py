from discord.ext import commands

cog_name = "debugging"


class debugging(commands.Cog):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    # Commands

    @commands.command(aliases=["dbe"], require_var_positional=True)
    @commands.is_owner()
    async def debug_exec(self, ctx: commands.Context, *, command: str):
        await ctx.reply(f"{eval(command)}")

    @commands.command(require_var_positional=True)
    @commands.is_owner()
    async def debug(self, ctx: commands.Context, *, command: str):
        self.bot.log.info(command)


async def setup(bot):
    await bot.add_cog(debugging(bot))


async def teardown(bot):
    pass

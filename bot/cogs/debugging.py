# debugging.py

from discord.ext import commands


class Debugging(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Commands

    @commands.command(aliases=["dbe"], require_var_positional=True)
    @commands.is_owner()
    async def debug_exec(self, ctx, *, command):
        await ctx.reply(f"{eval(command)}")

    @commands.command(require_var_positional=True)
    @commands.is_owner()
    async def debug(self, ctx, *, command):
        self.bot.log.info(command)

async def setup(bot):
    await bot.add_cog(Debugging(bot))

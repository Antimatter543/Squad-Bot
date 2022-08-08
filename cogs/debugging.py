import discord
from discord.ext import commands

class debugging(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    ### COMMANDS ###

    @commands.command(
        aliases=['dbe'],
        require_var_positional=True
    )
    @commands.is_owner()
    async def debug_exec(self, ctx, command):
        await ctx.reply(f'{eval(command)}')
        self.bot.logger.info(msg=f"{ctx.author} executed {command}")

async def setup(bot):
    await bot.add_cog(debugging(bot))
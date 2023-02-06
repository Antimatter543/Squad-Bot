# custom.py
# The location for all additional or custom commands

from discord.ext import commands


class Custom(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.log = bot.log


async def setup(bot):
    await bot.add_cog(Custom(bot))

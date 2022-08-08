# owner.py

### IMPORTS ###
import discord
from discord.ext import commands

from datetime import datetime

class owner(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.logger = bot.logger

    ### COMMANDS ###

    @commands.command(
        brief='Loads a cog extention',
        description='Loads a cog extention',
        require_var_positional=True
    )
    @commands.is_owner()
    async def load(self, ctx, cog):
        await self.bot.load_extension(f'cogs.{cog}')
        await ctx.reply(f'Loaded {str(cog)}!')
        self.logger.info(msg=f"{ctx.author} loaded {str(cog)}")

    @commands.command(
        brief='Unloads a cog extention',
        description='Unloads a cog extention',
        require_var_positional=True
    )
    @commands.is_owner()
    async def unload(self, ctx, cog):
        await self.bot.unload_extension(f'cogs.{cog}')
        await ctx.reply(f'Unloaded {str(cog)}!')
        self.logger.info(msg=f"{ctx.author} unloaded {str(cog)}")

    @commands.command(
        brief='Reloads a cog extention',
        description='Reloads a cog extention',
        require_var_positional=True
    )
    @commands.is_owner()
    async def reload(self, ctx, cog):
        await self.bot.reload_extension(f'cogs.{cog}')
        await ctx.reply(f'Reloaded {str(cog)}!')
        self.logger.info(msg=f"{ctx.author} reloaded {str(cog)}")

    @commands.command(
        brief='Syncs the application tree',
        description='Syncs the application tree'
    )
    @commands.is_owner()
    async def sync(self, ctx, guild_id):
        if guild_id:
            if guild_id == "guild" or guild_id == "~":
                guild_id = ctx.guild.id
            tree = await self.bot.tree.sync(guild=discord.Object(id=guild_id))
        else:
            tree = await self.bot.tree.sync()

        await ctx.reply(f'{len(tree)} synced!')
        self.logger.info(msg=f"{ctx.author} synced the tree({len(tree)}): {tree}")

    @commands.command(
        brief='Shows the bot log',
        description='Shows the bot log'
    )
    @commands.is_owner()
    async def logs(self, ctx):
        """Upload the bot logs"""
        await ctx.reply(file=discord.File(fp="bot.log", filename="bot.log"))

    @commands.command(name="uptime")
    @commands.is_owner()
    async def show_uptime(self, ctx: commands.Context):
        """Show the bot uptime."""
        uptime = datetime.now() - self.bot.uptime
        await ctx.reply(f"<t:{round(self.bot.uptime.timestamp())}:R> ||`{uptime}`||")

    @commands.command(
        brief='Shutdown the bot',
        description='Shutdown the bot'
    )
    @commands.is_owner()
    async def shutdown(self, ctx: commands.Context):
        """Shutdown the bot."""
        await ctx.send(f":wave: `{self.bot.user.name}` is shutting down...")

        await self.bot.close()

async def setup(bot):
    await bot.add_cog(owner(bot))
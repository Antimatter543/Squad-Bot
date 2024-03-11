from datetime import datetime
from typing import Literal, Optional

import discord
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Greedy

cog_name = "administrative"


class administrative(commands.Cog):
    def __init__(self, bot):
        super().__init__()
        self.log = bot.log

    admin_group = app_commands.Group(name="admin", description="Administrative commands")

    # Commands
    @admin_group.command(
        description="Loads a cog extension",
    )
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.guild_only()
    async def load(self, interaction: discord.Interaction, cog: str):
        await interaction.response.defer(ephemeral=True)
        await interaction.client.load_extension(f"cogs.{cog}")
        await interaction.followup.send(f"Loaded {str(cog)}!", ephemeral=True)

    @admin_group.command(
        description="Unloads a cog extension",
    )
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.guild_only()
    async def unload(self, interaction: discord.Interaction, cog: str):
        await interaction.response.defer(ephemeral=True)
        await interaction.client.unload_extension(f"cogs.{cog}")
        await interaction.followup.send(f"Unloaded {str(cog)}!", ephemeral=True)

    @admin_group.command(
        description="Reloads a cog extension",
    )
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.guild_only()
    async def reload(self, interaction: discord.Interaction, cog: str):
        await interaction.response.defer(ephemeral=True)
        await interaction.client.reload_extension(f"cogs.{cog}")
        await interaction.followup.send(f"Reloaded {str(cog)}!", ephemeral=True)

    @commands.command(description="Syncs the application tree")
    @commands.guild_only()
    @commands.is_owner()
    async def sync(
        self, ctx: commands.Context, guilds: Greedy[discord.Object], spec: Optional[Literal["~", "*", "^"]] = None
    ) -> None:
        if not guilds:
            if spec == "~":
                synced = await ctx.bot.tree.sync(guild=ctx.guild)
            elif spec == "*":
                ctx.bot.tree.copy_global_to(guild=ctx.guild)
                synced = await ctx.bot.tree.sync(guild=ctx.guild)
            elif spec == "^":
                ctx.bot.tree.clear_commands(guild=ctx.guild)
                await ctx.bot.tree.sync(guild=ctx.guild)
                synced = []
            else:
                synced = await ctx.bot.tree.sync()

            await ctx.send(f"Synced {len(synced)} commands {'globally' if spec is None else 'to the current guild.'}")
            return

        ret = 0
        for guild in guilds:
            try:
                await ctx.bot.tree.sync(guild=guild)
            except discord.HTTPException:
                pass
            else:
                ret += 1

        await ctx.send(f"Synced the tree to {ret}/{len(guilds)}.")

    @admin_group.command(description="Shows the bot log")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.guild_only()
    async def logs(self, interaction: discord.Interaction):
        """Upload the bot logs"""
        await interaction.response.send_message(file=discord.File(fp="bot.log", filename="bot.log"))

    @app_commands.command(name="uptime")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.guild_only()
    async def show_uptime(self, interaction: discord.Interaction):
        """Show the bot uptime."""
        uptime = datetime.now() - interaction.client.uptime
        await interaction.response.send_message(f"<t:{round(interaction.client.uptime.timestamp())}:R> ||`{uptime}`||")

    @admin_group.command(description="Shutdown the bot")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.guild_only()
    async def shutdown(self, interaction: discord.Interaction):
        """Shutdown the bot."""
        await interaction.response.send_message(f":wave: `{interaction.client.user.name}` is shutting down...")

        await interaction.client.close()

    @app_commands.command(
        description="Clears a number of previous messages from a channel",
    )
    @app_commands.checks.has_permissions(manage_messages=True)
    @app_commands.checks.bot_has_permissions(manage_messages=True)
    async def clear(self, interaction: discord.Interaction, amount: int = 5):
        if not hasattr(interaction.channel, "purge"):
            raise commands.CommandError("Channel can not be purged")
        await interaction.channel.purge(limit=amount, before=interaction.message)
        await interaction.message.delete()


async def setup(bot):
    await bot.add_cog(administrative(bot))


async def teardown(bot):
    pass

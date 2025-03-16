from datetime import datetime, timedelta
from typing import Literal, Optional
import re

import discord
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Greedy
import os

from bot.lib.date import _time

cog_name = "administrative"

cogs_directory = os.path.join(os.path.dirname(__file__), "")
available_cogs = [f[:-3] for f in os.listdir(cogs_directory) if f.endswith(".py") and f != "__init__.py"]

class administrative(commands.Cog):
    def __init__(self, bot):
        super().__init__()
        self.log = bot.log

    admin_group = app_commands.Group(name="admin", description="Administrative commands")

    # Commands

    @app_commands.command(name="cogs", description="Cog management")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.choices(
        action=[app_commands.Choice(name=str(i), value=i) for i in ["load", "unload", "reload", "list"]],
        cog=[app_commands.Choice(name=cog, value=cog) for cog in available_cogs],
    )
    @app_commands.describe(
        cog="The cog to manage",
    )
    @app_commands.guild_only()
    async def cogs(self, interaction: discord.Interaction, action: str, cog: Optional[str] = None):
        """Cog management"""
        await interaction.response.defer(ephemeral=True)
        if action == "list":
            cog_states = []
            for cog in available_cogs:
                if f"cogs.{cog}" in interaction.client.extensions:
                    cog_states.append(f"\u2705 | {cog}")
                else:
                    cog_states.append(f"\u274c | {cog}")
            cog_list = "\n".join(cog_states) if cog_states else "No cogs available."
            await interaction.followup.send(f"Available cogs:\n{cog_list}")
            return
        match action:
            case "load":
                await interaction.client.load_extension(f"cogs.{cog}")
            case "unload":
                await interaction.client.unload_extension(f"cogs.{cog}")
            case "reload":
                await interaction.client.reload_extension(f"cogs.{cog}")
        await interaction.followup.send(f"{action.capitalize()}ed {cog}!")

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
        """Clears a number of previous messages from a channel"""
        if not hasattr(interaction.channel, "purge"):
            raise commands.CommandError("Channel can not be purged")
        await interaction.response.defer(ephemeral=True)
        await interaction.channel.purge(limit=amount, before=interaction.message)
        await interaction.message.delete()
        await interaction.response.send_message(f"Cleared {amount} messages", ephemeral=True)

    @app_commands.command(
        description="Alert a channel that the bot is going down for maintenance"
    )
    @app_commands.describe(
        channel="The channel to alert",
        start_time="The time to start maintenance. Date Format: [h,m,s] | e.g. 12h30m or 1d30s or 5m",
        duration="Length of expected maintenance window. Date Format: [h,m,s] | e.g. 12h30m or 1h30s or 5m",
    )
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.guild_only()
    async def maintenance(self, interaction: discord.Interaction, channel: discord.TextChannel, start_time: str, duration: str):
        await interaction.response.defer(ephemeral=True)
        fmts = {"s": "seconds", "m": _time.minute, "h": _time.hour, "d": _time.day}
        fmt_re = re.compile(r"(\d+h)?(\d+m)?(\d+s)?")
        start_matches = re.findall(fmt_re, start_time)
        dur_matches = re.findall(fmt_re, duration)
        
        if not start_matches or not dur_matches:
            await interaction.followup.send("Invalid time format")
            return        
        
        time_start = datetime.now().replace(microsecond=0)
        for match in start_matches:
            for group in match:
                if not group:
                    continue
                c = group[-1]
                if c == "s":
                    time_start.replace(second=int(group[:-1]))
                elif c == "m":
                    time_start.replace(minute=int(group[:-1]))
                elif c == "h":
                    time_start.replace(hour=int(group[:-1]))
        
        time_s = 0
        for match in dur_matches:
            for group in match:
                if not group:
                    continue
                time_s += int(group[:-1]) * fmts[group[-1]]
                
        time_end = time_start + timedelta(seconds=time_s)
        
        time_start_ts = round(datetime.timestamp(time_start))
        time_end_ts = round(datetime.timestamp(time_end))
        
        embed = discord.Embed(
            title="Maintenance Alert",
            description=f"Bot going down for maintenance at <t:{time_start_ts}:f> (<t:{time_start_ts}:R>) for {duration}.\nExpected back <t:{time_end_ts}:R> (<t:{time_end_ts}:f>)",
            color=discord.Color.gold()
        )
        await channel.send(embed=embed)
        await interaction.followup.send("Alerted channel")
        
        
        
async def setup(bot):
    await bot.add_cog(administrative(bot))


async def teardown(bot):
    pass

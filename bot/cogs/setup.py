import re
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from bot.database.models import StatisticsConfig

cog_name = "setup"


class setupCop(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__()
        self.bot = bot
        self.log = bot.log

    setup_group = app_commands.Group(name="setup", description="Setup a feature")

    @setup_group.command(
        description="Configure the void screams feature",
    )
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.guild_only()
    async def statistics(
        self,
        interaction: discord.Interaction,
        channel: Optional[discord.TextChannel] = None,
        regexp_primary: Optional[str] = None,
        regexp_secondary: Optional[str] = None,
        minor_threshold: Optional[int] = None,
        major_threshold: Optional[int] = None,
        minor_role: Optional[discord.Role] = None,
        major_role: Optional[discord.Role] = None,
    ):
        await interaction.response.defer(ephemeral=True)
        module_name = "statistics"

        if (modules := self.bot.modules.get(module_name)) is None:
            return await interaction.followup.send(f"Error: {module_name} module not loaded")

        if (module := modules.get(interaction.guild_id)) is None:
            return await interaction.followup.send(
                f"Error: {module_name} module not loaded in {interaction.guild.name}"
            )
        # Set module config attributes
        if regexp_primary:
            try:
                regexp_primary = re.compile(regexp_primary)
            except re.error:
                return await interaction.followup.send("Error: Primary Regex invalid")
        if regexp_secondary:
            try:
                regexp_secondary = re.compile(regexp_secondary)
            except re.error:
                return await interaction.followup.send("Error: Secondary Regex invalid")
        if minor_threshold is not None and minor_threshold < 0:
            return await interaction.followup.send("Error: Minor Threshold must be greater than 0")
        if major_threshold is not None and major_threshold < 0:
            return await interaction.followup.send("Error: Major Threshold must be greater than 0")
        if minor_threshold is not None and major_threshold is not None and minor_threshold > major_threshold:
            return await interaction.followup.send("Error: Minor Threshold must be less than Major Threshold")

        attrs = [
            "channel",
            "regexp_primary",
            "regexp_secondary",
            "minor_threshold",
            "major_threshold",
            "minor_role",
            "major_role",
        ]

        for attr in attrs:
            if (value := locals()[attr]) is not None:
                setattr(module, attr, value)

        # Save to database
        async with self.bot.session as session:
            row = await session.get(StatisticsConfig, interaction.guild_id)
            channel_id = channel.id if channel else module.channel.id
            minor_role_id = minor_role.id if minor_role else module.minor_role.id
            major_role_id = major_role.id if major_role else module.major_role.id
            regexp_primary = regexp_primary if regexp_primary else module.regexp_primary.pattern
            regexp_secondary = regexp_secondary if regexp_secondary else module.regexp_secondary.pattern
            minor_threshold = minor_threshold if minor_threshold else module.minor_threshold
            major_threshold = major_threshold if major_threshold else module.major_threshold
            if row is None:
                row = StatisticsConfig(
                    guild_id=interaction.guild_id,
                    channel_id=channel_id,
                    regexp_primary=regexp_primary,
                    regexp_secondary=regexp_secondary,
                    minor_threshold=minor_threshold,
                    major_threshold=major_threshold,
                    minor_role_id=minor_role_id,
                    major_role_id=major_role_id,
                )
            else:
                row.channel_id = channel_id
                row.regexp_primary = regexp_primary
                row.regexp_secondary = regexp_secondary
                row.minor_threshold = minor_threshold
                row.major_threshold = major_threshold
                row.minor_role_id = minor_role_id
                row.major_role_id = major_role_id
            session.add(row)
            await session.commit()
        # Send response
        embed = discord.Embed(title=f"{module_name}", color=discord.Color.magenta())

        if module.channel.id is not None:
            embed.add_field(name="Channel", value=module.channel.mention)
        if module.regexp_primary is not None:
            embed.add_field(name="Priamry Regex", value=module.regexp_primary.pattern)
        if module.regexp_secondary is not None:
            embed.add_field(name="Secondary Regex", value=module.regexp_secondary.pattern)
        if module.minor_threshold is not None:
            embed.add_field(name="Minor Threshold", value=module.minor_threshold)
        if module.minor_role.id is not None:
            embed.add_field(name="Minor Role", value=module.minor_role.mention)
        if module.major_threshold is not None:
            embed.add_field(name="Major Threshold", value=module.major_threshold)
        if module.major_role.id is not None:
            embed.add_field(name="Major Role", value=module.major_role.mention)

        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(setupCop(bot))


async def teardown(bot):
    pass

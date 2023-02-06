# administrative.py

import discord
from discord import app_commands
from discord.ext import commands

from bot.settings import admin_roles


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.log = bot.log

    @commands.command(
        name="clear",
        brief="Clears a number of your past messages",
        description="Clears a number of previous messages from a channel",
    )
    @commands.has_any_role(*admin_roles)
    @commands.bot_has_permissions(manage_messages=True)
    @commands.has_permissions(manage_messages=True)
    async def clear(self, ctx: commands.Context, amount=5):
        await ctx.channel.purge(limit=amount, before=ctx.message)
        await ctx.message.delete()

    @app_commands.command(
        name="add_role",
        description="Clears a number of previous messages from a channel",
    )
    @app_commands.describe(rtype="Permissions Type")
    @app_commands.choices(
        action=[app_commands.Choice(name=name, value=name) for name in ["add", "remove"]],
        rtype=[app_commands.Choice(name=name, value=name) for name in ["admin", "elevated"]],
    )
    @app_commands.checks.has_any_role(*admin_roles)
    @commands.bot_has_permissions(manage_roles=True)
    @commands.has_permissions(manage_roles=True)
    @app_commands.guilds(discord.Object(id=809997432011882516), discord.Object(id=676253010053300234))
    async def edit_role_premissions(self, interaction: discord.Interaction, action: str, rtype: str, role_name: str):
        guild = interaction.guild
        if guild is None:
            return
        role = discord.utils.get(guild.roles, name=role_name)
        if role is None:
            await interaction.response.send_message("A role with that name could not be found", ephemeral=True)

        if rtype == "admin":
            if action == "add":
                await self.bot.settings.add_admin_role(role_name)
            elif action == "remove":
                await self.bot.settings.remove_admin_role(role_name)
            else:
                raise NotImplementedError("This action has not been implemented")
        elif rtype == "elevated":
            if action == "add":
                await self.bot.settings.add_elevated_role(role_name)
            elif action == "remove":
                await self.bot.settings.remove_elevated_role(role_name)
            else:
                raise NotImplementedError("This action has not been implemented")

        else:
            raise NotImplementedError("This role has not been implemented")


async def setup(bot):
    await bot.add_cog(Admin(bot))

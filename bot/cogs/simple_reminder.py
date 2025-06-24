import asyncio
import re
from datetime import datetime, timedelta

import discord
from discord import app_commands
from discord.ext import commands, tasks
from sqlalchemy import Sequence, select

from bot.database.models import Reminder
from bot.lib.date import now_tz, _time

cog_name = "simple_reminder"

# Only mention the user who created the reminder
mention_only_user = discord.AllowedMentions(everyone=False, users=True, roles=False)


class simple_reminder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.log = bot.log
        self.check_reminders_task = None
        
    async def _init(self):
        """Initialize the cog with database tables and start the polling task."""
        self.log.info(f"Initialised {self.__class__.__name__}")

        if self.bot.db is None:
            raise Exception("This cog requires a database to be enabled.")

        # Start the reminder checking loop
        self.check_reminders_task = self.check_reminders.start()

    async def _destroy(self):
        """Cleanup when cog is unloaded."""
        if self.check_reminders_task:
            self.check_reminders_task.cancel()
    
    @tasks.loop(seconds=60)
    async def check_reminders(self):
        """Check for due reminders every minute instead of using sleep()."""
        try:
            now = now_tz()
            self.log.debug(f"Checking for reminders at {now}")
            
            async with self.bot.session as session:
                # Query only reminders that are due and not repeating
                stmt = select(Reminder).where(Reminder.send_time <= now).where(Reminder.repeat == False)
                due_reminders: Sequence[Reminder] = (await session.scalars(stmt)).all()
                
                if due_reminders:
                    self.log.info(f"Found {len(due_reminders)} due reminders")
                    
                for reminder in due_reminders:
                    rid, user_id, channel_id, message, send_time, requested_time, repeat = reminder
                    
                    try:
                        # Try to fetch the channel - this could fail if channel deleted
                        channel = await self.bot.fetch_channel(channel_id)
                        
                        # Format timestamps for display
                        req_ts = int(requested_time.timestamp())
                        send_ts = int(send_time.timestamp())
                        now_ts = int(now.timestamp())
                        
                        # Create a nice embed for the reminder
                        embed = discord.Embed(
                            title="Reminder",
                            color=discord.Color.blue(),
                            description=f"<@{user_id}>, here's your reminder!"
                        )
                        embed.add_field(name="Message", value=message, inline=False)
                        embed.add_field(
                            name="Timing", 
                            value=f"Requested: <t:{req_ts}:F>\nScheduled: <t:{send_ts}:F>\nDelivered: <t:{now_ts}:F>", 
                            inline=False
                        )
                        
                        # Add a small delay between messages to avoid rate limits
                        await channel.send(
                            content=f"<@{user_id}>", 
                            embed=embed,
                            allowed_mentions=mention_only_user
                        )
                        
                        # Remove the reminder from database after sending
                        await session.delete(reminder)
                        
                    except discord.errors.NotFound:
                        self.log.warning(f"Channel {channel_id} not found for reminder {rid}")
                        await session.delete(reminder)
                    except Exception as e:
                        self.log.error(f"Error sending reminder {rid}: {e}")
                        # Don't delete the reminder on other errors - it will retry next cycle
                        
                # Commit all changes to the database
                await session.commit()
                
        except Exception as e:
            self.log.error(f"Error in check_reminders task: {e}")
            # Task will automatically restart due to the loop decorator

    @check_reminders.before_loop
    async def before_check_reminders(self):
        """Wait until the bot is ready before starting the loop."""
        await self.bot.wait_until_ready()

    async def add_reminder(self, user_id, channel_id, message, send_time, requested_time=None):
        """Add a new reminder to the database."""
        if requested_time is None:
            requested_time = now_tz()
            
        async with self.bot.session as session:
            reminder = Reminder(
                user_id=user_id,
                channel_id=channel_id,
                message=message,
                send_time=send_time,
                requested_time=requested_time,
                repeat=False,  # Simple reminders don't repeat
            )
            session.add(reminder)
            await session.commit()
            await session.refresh(reminder)
            return reminder.id

    @commands.command(
        name="remind", 
        aliases=["remindme", "reminder"],
        brief="Set a reminder",
        description="Set a reminder with natural language time format (e.g. '10m', '2h30m', '1d', '2w')",
        help="Examples:\n!remind 10m Take out the trash\n!remind 1d2h Check the mail\n!remind 1w Call mom"
    )
    async def remind_command(self, ctx, time_str: str, *, message: str):
        """Text command for setting reminders with simple time format."""
        # Parse the time string (e.g. "5m", "1h30m", "2d", "1w")
        seconds = self._parse_time_string(time_str)
        
        if seconds <= 0:
            await ctx.reply("⚠️ Invalid time format. Examples: '10m', '2h30m', '1d', '2w'")
            return
            
        if seconds > 60 * 60 * 24 * 365:  # 1 year max
            await ctx.reply("⚠️ Reminder time too long. Maximum is 1 year.")
            return
        
        # Calculate the time when the reminder should be sent
        now = now_tz()
        remind_time = now + timedelta(seconds=seconds)
        remind_time_ts = int(remind_time.timestamp())
        
        # Add the reminder to database
        reminder_id = await self.add_reminder(
            ctx.author.id, 
            ctx.channel.id, 
            message, 
            remind_time,
            now
        )
        
        # Send confirmation
        embed = discord.Embed(
            title="✅ Reminder Set",
            color=discord.Color.green(),
            description=f"I'll remind you <t:{remind_time_ts}:R>"
        )
        embed.add_field(name="Message", value=message, inline=False)
        embed.set_footer(text=f"Reminder ID: {reminder_id}")
        
        await ctx.reply(embed=embed)
    
    @app_commands.command(
        name="remind",
        description="Set a reminder for later"
    )
    @app_commands.describe(
        time_format="Time until reminder (e.g., 10m, 2h30m, 1d, 1w3d)",
        message="What to remind you about"
    )
    async def remind_slash(self, interaction: discord.Interaction, time_format: str, message: str):
        """Slash command version of the reminder."""
        await interaction.response.defer(ephemeral=False)
        
        # Parse the time string
        seconds = self._parse_time_string(time_format)
        
        if seconds <= 0:
            await interaction.followup.send("⚠️ Invalid time format. Examples: '10m', '2h30m', '1d', '2w'", ephemeral=True)
            return
            
        if seconds > 60 * 60 * 24 * 365:  # 1 year max
            await interaction.followup.send("⚠️ Reminder time too long. Maximum is 1 year.", ephemeral=True)
            return
        
        # Calculate the time when the reminder should be sent
        now = now_tz()
        remind_time = now + timedelta(seconds=seconds)
        remind_time_ts = int(remind_time.timestamp())
        
        # Add the reminder to database
        reminder_id = await self.add_reminder(
            interaction.user.id, 
            interaction.channel_id, 
            message, 
            remind_time,
            now
        )
        
        # Send confirmation
        embed = discord.Embed(
            title="✅ Reminder Set",
            color=discord.Color.green(),
            description=f"I'll remind you <t:{remind_time_ts}:R>"
        )
        embed.add_field(name="Message", value=message, inline=False)
        embed.set_footer(text=f"Reminder ID: {reminder_id}")
        
        await interaction.followup.send(embed=embed)

    @app_commands.command(
        name="list_reminders",
        description="List all your pending reminders"
    )
    async def list_reminders(self, interaction: discord.Interaction):
        """Show all reminders for the current user."""
        await interaction.response.defer(ephemeral=True)
        
        async with self.bot.session as session:
            stmt = select(Reminder).where(Reminder.user_id == interaction.user.id)
            reminders = (await session.scalars(stmt)).all()
            
            if not reminders:
                await interaction.followup.send("You have no active reminders.", ephemeral=True)
                return
                
            embed = discord.Embed(
                title="Your Reminders",
                color=discord.Color.blue(),
                description=f"You have {len(reminders)} active reminder(s)"
            )
            
            for reminder in reminders:
                rid, _, channel_id, message, send_time, _, _ = reminder
                send_ts = int(send_time.timestamp())
                
                # Try to get channel name
                channel_name = "Unknown channel"
                try:
                    channel = await self.bot.fetch_channel(channel_id)
                    channel_name = f"#{channel.name}"
                except:
                    pass
                
                embed.add_field(
                    name=f"ID: {rid} • Due <t:{send_ts}:R>",
                    value=f"**Channel:** {channel_name}\n**Message:** {message}",
                    inline=False
                )
                
            await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(
        name="cancel_reminder",
        description="Cancel one of your reminders"
    )
    @app_commands.describe(
        reminder_id="The ID of the reminder to cancel"
    )
    async def cancel_reminder(self, interaction: discord.Interaction, reminder_id: int):
        """Cancel a specific reminder by ID."""
        await interaction.response.defer(ephemeral=True)
        
        async with self.bot.session as session:
            # Find the reminder and verify it belongs to the user
            stmt = select(Reminder).where(Reminder.id == reminder_id).where(Reminder.user_id == interaction.user.id)
            reminder = (await session.scalars(stmt)).first()
            
            if not reminder:
                await interaction.followup.send(
                    f"❌ Reminder #{reminder_id} not found or doesn't belong to you.",
                    ephemeral=True
                )
                return
                
            # Delete the reminder
            await session.delete(reminder)
            await session.commit()
            
            await interaction.followup.send(
                f"✅ Reminder #{reminder_id} has been cancelled.",
                ephemeral=True
            )

    def _parse_time_string(self, time_str: str) -> int:
        """
        Parse time strings like '1d2h30m' into seconds.
        Supports: s (seconds), m (minutes), h (hours), d (days), w (weeks)
        """
        time_str = time_str.lower().strip()
        total_seconds = 0
        
        # Define regex pattern for different time units
        pattern = r'(\d+w)?(\d+d)?(\d+h)?(\d+m)?(\d+s)?'
        match = re.fullmatch(pattern, time_str)
        
        if not match or not any(match.groups()):
            return 0
            
        # Extract and calculate seconds for each unit
        parts = match.groups()
        units = {'w': _time.week, 'd': _time.day, 'h': _time.hour, 'm': _time.minute, 's': 1}
        
        for i, unit in enumerate(['w', 'd', 'h', 'm', 's']):
            if parts[i]:
                # Extract number and multiply by unit value
                value = int(parts[i][:-1])
                total_seconds += value * units[unit]
                
        return total_seconds


async def setup(bot):
    cog = simple_reminder(bot)
    await cog._init()
    await bot.add_cog(cog)


async def teardown(bot):
    cog = bot.get_cog("simple_reminder")
    if cog:
        await cog._destroy()

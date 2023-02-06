# reminder.py

import asyncio
import re
from contextlib import suppress
from datetime import datetime, timedelta

import discord
from discord import app_commands
from discord.ext import commands

from bot.lib.utils import get_tz, now_tz
from bot.settings import admin_roles, elevated_roles

mention_only_user = discord.AllowedMentions(everyone=False, users=False, roles=False)


class _time:
    second = 1
    minute = second * 60
    hour = minute * 60
    day = hour * 24
    week = day * 7

    @staticmethod
    def convert_seconds(*, weeks: int = 0, days: int = 0, hours: int = 0, minutes: int = 0, seconds: int = 0):
        return seconds + minutes * _time.minute + hours * _time.hour + days * _time.day + weeks * _time.week

    @staticmethod
    def seconds_to_string(seconds=0):
        time = timedelta(seconds=seconds)
        mm, ss = divmod(time.seconds, 60)
        hh, mm = divmod(mm, 60)
        return f"{time.days} days, {hh} hours, {mm} minutes, {ss} seconds"


class RepeatingReminder:
    def __init__(self, bot, aid: int, cid: int, message: str, interval: int, requested_time: datetime, delay=0) -> None:
        self.bot = bot
        self.started = False
        self.stopped = False
        self._task = None

        self.aid = aid
        self.cid = cid
        self.message = message
        self.interval = interval
        self.requested_time = requested_time
        self.delay = delay

    async def start(self):
        if self.stopped:
            return
        if not self.started:
            self.started = True
            self._task = asyncio.ensure_future(self._run())

    async def stop(self):
        self.stopped = True
        if self.started:
            self.started = False
            # Stop task and await it stopped:
            if self._task is not None:
                was_cancelled = self._task.cancel()
                if not was_cancelled:
                    self.bot.log.error("Failed to cancel task")
                with suppress(asyncio.CancelledError):
                    self.bot.log.error("Failed to cancel task")
                    await self._task

    async def _run(self):
        while True:
            if self.delay:
                await asyncio.sleep(self.delay)
                await self.send_message()
                self.delay = 0

            await asyncio.sleep(self.interval)
            await self.send_message()

    async def send_message(self):
        channel = self.bot.get_channel(self.cid)
        now = round(datetime.timestamp(now_tz()))
        then = round(datetime.timestamp(self.requested_time))
        embed = discord.Embed(
            title=f"Scheduled Reminder",
            description=f"<@{self.aid}>'s repeating reminder\nSent <t:{now}:T> <t:{now}:d>\nReqested: <t:{then}:T> <t:{then}:d>",
        )
        embed.add_field(name="Message", value=f"{self.message}")
        embed.set_footer(text=f"Repeats every: {_time.seconds_to_string(self.interval)}")

        await channel.send(embed=embed, allowed_mentions=mention_only_user)


class reminders(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.log = bot.log
        self.repeating: dict[int, RepeatingReminder] = {}
        self.tasks = []

    async def _init(self):
        async def start_reminder(delay: int, rid: int, aid: int, cid: int, requested_time: datetime, message: str):
            await asyncio.sleep(delay)
            channel = self.bot.get_channel(cid)
            then = round(datetime.timestamp(requested_time))
            msg = f"<@{aid}>, this is your reminder (loaded from backup)\nReqested <t:{then}:T> <t:{then}:d>"
            msg += f"\nYou wanted to say: {message}"
            await channel.send(msg, allowed_mentions=mention_only_user)
            await self.remove_reminder(aid, rid)

        query = (
            "CREATE TABLE IF NOT EXISTS dc_reminders (\n"
            "id serial PRIMARY KEY,\n"
            "user_id BIGINT NOT NULL,\n"
            "channel_id BIGINT NOT NULL,\n"
            "message TEXT NOT NULL,\n"
            "send_time TIMESTAMP WITH TIME ZONE NOT NULL,\n"
            "requested_time TIMESTAMP WITH TIME ZONE NOT NULL,\n"
            "repeat BOOLEAN\n"
            ");"
        )
        async with self.bot.db.acquire() as connection:
            await connection.execute(query)

            query = "SELECT * FROM dc_reminders;"
            reminders = await connection.fetch(query)

            for reminder in reminders:
                rid, aid, cid, msg, send_time, requested_time, repeat = reminder
                now = now_tz()
                if bool(repeat):
                    interval = int((send_time - requested_time).total_seconds())
                    delta = int((now - requested_time).total_seconds())
                    self.repeating[rid] = RepeatingReminder(
                        self.bot, aid, cid, msg, interval, requested_time, interval - (delta % interval)
                    )
                    await self.repeating[rid].start()
                else:
                    # remove reminders that should have already happened
                    if send_time < now:
                        await self.remove_reminder(aid, rid)
                    else:  # Set up missing reminder
                        delay = int((send_time - now).total_seconds())
                        self.tasks.append(
                            asyncio.create_task(start_reminder(delay, rid, aid, cid, requested_time, msg))
                        )

    async def _destroy(self):
        for _, reminder in self.repeating.items():
            await reminder.stop()
        for task in self.tasks:
            task.cancel()

    async def add_reminder(self, user_id, channel_id, message, send_time, requested_time, repeat=False):
        async with self.bot.db.acquire() as connection:
            query = (
                "INSERT INTO dc_reminders "
                "(user_id, channel_id, message, send_time, requested_time, repeat) "
                "VALUES ($1, $2, $3, $4, $5, $6);"
            )
            await connection.execute(query, user_id, channel_id, message, send_time, requested_time, repeat)
            row = await connection.fetchrow(
                "SELECT * FROM dc_reminders WHERE user_id = $1 AND requested_time = $2;", user_id, requested_time
            )
            return row["id"]

    async def remove_reminder(self, aid: int, rid: int):
        async with self.bot.db.acquire() as connection:
            query = "DELETE FROM dc_reminders WHERE id = $1 and user_id = $2;"
            await connection.execute(query, rid, aid)
        if rid in self.repeating:
            await self.repeating[rid].stop()
            del self.repeating[rid]

    async def _reminder(self, ctx: commands.Context | discord.Interaction, delta_s: int, message: str, repeat=False):
        """
        Sends the given message to the context after waiting {delta} seconds

        :param ctx: message context
        :param delta: time to wait in seconds
        :param message: message to send
        """
        now = now_tz()

        now_ts = round(datetime.timestamp(now))
        remind_time = now + timedelta(seconds=delta_s)
        remind_time_ts = round(datetime.timestamp(remind_time))

        if isinstance(ctx, commands.Context):
            send_f = ctx.reply
            author = ctx.author
        elif isinstance(ctx, discord.Interaction):
            send_f = ctx.followup.send
            author = ctx.user
        else:
            return

        await send_f(f"Your reminder will be sent <t:{remind_time_ts}:R>.", ephemeral=True)

        rid = await self.add_reminder(author.id, ctx.channel.id, message, remind_time, now, repeat)

        if not repeat:
            msg = f"{author.mention}, this is your reminder\nReqested <t:{now_ts}:T> <t:{now_ts}:d>"
            msg += f"\nYou wanted to say: {message}"
            await asyncio.sleep(delta_s)

            await send_f(msg, ephemeral=True)
            await self.remove_reminder(author.id, rid)
        else:
            self.repeating[rid] = RepeatingReminder(self.bot, author.id, ctx.channel.id, message, delta_s, now)
            await self.repeating[rid].start()

    # Commands
    @commands.command(
        name="reminder",
        aliases=["rm"],
        brief="Sets a one off reminder",
        description="Reminds you of something.",
    )
    async def reminder(self, ctx: commands.Context, fmt: str, *, message: str):

        fmts = {"s": 1, "m": 60, "h": 60 * 60, "d": 60 * 60 * 24}
        fmt_re = re.compile(r"(\d+d)?(\d+h)?(\d+m)?(\d+s)?")
        matches = re.findall(fmt_re, fmt)

        time_s = 0
        for match in matches:
            for group in match:
                if not group:
                    continue
                time_s += int(group[:-1]) * fmts[group[-1]]

        await self._reminder(ctx, time_s, message)

    @app_commands.command(name="reminder", description="Reminds you of something.")
    @app_commands.describe(
        days="Days.", hours="Hours.", minutes="Minutes.", seconds="Seconds.", message="Your reminder message."
    )
    @app_commands.choices(
        hours=[app_commands.Choice(name=str(i), value=i) for i in range(0, 24)],
        minutes=[app_commands.Choice(name=str(i), value=i) for i in range(0, 56, 5)],
        seconds=[app_commands.Choice(name=str(i), value=i) for i in range(0, 56, 5)],
    )
    @app_commands.guilds(discord.Object(id=809997432011882516), discord.Object(id=676253010053300234))
    async def reminderApp(
        self, interaction: discord.Interaction, days: int, hours: int, minutes: int, seconds: int, *, message: str
    ):
        time_s = _time.convert_seconds(days=days, hours=hours, minutes=minutes, seconds=seconds)
        await interaction.response.defer(ephemeral=True)
        await self._reminder(interaction, time_s, message)

    @app_commands.command(name="repeating_reminder", description="Reminds you of something (Repeating). 1 Hour minimum")
    @app_commands.describe(message="Your reminder message.")
    @app_commands.choices(
        weeks=[app_commands.Choice(name=str(i), value=i) for i in range(0, 16)],
        hours=[app_commands.Choice(name=str(i), value=i) for i in range(0, 24)],
        minutes=[app_commands.Choice(name=str(i), value=i) for i in range(0, 56, 5)],
    )
    @app_commands.guilds(discord.Object(id=809997432011882516), discord.Object(id=676253010053300234))
    async def reminderRepeating(
        self, interaction: discord.Interaction, weeks: int, days: int, hours: int, minutes: int, *, message: str
    ):
        await interaction.response.defer(ephemeral=True)
        time_s = _time.convert_seconds(weeks=weeks, days=days, hours=hours, minutes=minutes)
        if time_s < _time.convert_seconds(hours=12):
            await interaction.response.send_message(
                "Repeating reminders must have at least a 12 hour interval", ephemeral=True
            )
            return
        await self._reminder(interaction, time_s, message, repeat=True)

    @app_commands.command(name="my_reminders", description="See your reminders")
    @app_commands.guilds(discord.Object(id=809997432011882516), discord.Object(id=676253010053300234))
    async def myReminders(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        query = "SELECT * FROM dc_reminders WHERE user_id = $1;"
        async with self.bot.db.acquire() as connection:
            reminders = await connection.fetch(query, interaction.user.id)

            embed = discord.Embed(title=f"Reminders", description=f"{interaction.user.display_name}'s reminders.")
            if reminders:
                msg = "\n".join(
                    [
                        (
                            f"rid={rid}: (repeating={repeat}) {message} "
                            f"to be sent at <t:{round(datetime.timestamp(send_time))}:f>"
                            f"- requested <t:{round(datetime.timestamp(requested_time))}:f> "
                        )
                        for rid, _, _, message, send_time, requested_time, repeat in reminders
                    ]
                )
            else:
                msg = "No reminders are set"

            embed.add_field(name="Reminders", value=msg)
            await interaction.followup.send(embed=embed, ephemeral=True, allowed_mentions=mention_only_user)

    @app_commands.command(name="delete_reminder", description="Delete a repeating reminder")
    @app_commands.describe(rid="Reminder id (see myReminders command).")
    @app_commands.guilds(discord.Object(id=809997432011882516), discord.Object(id=676253010053300234))
    async def deleteReminders(self, interaction: discord.Interaction, rid: int):
        await interaction.response.defer(ephemeral=True)
        await self.remove_reminder(interaction.user.id, rid)
        await interaction.followup.send("Deleted reminder", ephemeral=True)

    @commands.hybrid_command(name="allreminders", brief="See active reminders", with_app_command=True)
    @commands.has_any_role(*elevated_roles, *admin_roles)
    @app_commands.guilds(discord.Object(id=809997432011882516), discord.Object(id=676253010053300234))
    async def allReminders(self, ctx: commands.Context):
        await ctx.defer(ephemeral=True)
        query = "SELECT * FROM dc_reminders;"
        async with self.bot.db.acquire() as connection:
            reminders = await connection.fetch(query)
            embed = discord.Embed(title=f"Reminders", description=f"All reminders.")
            if reminders:
                msg = "\n".join(
                    [
                        (
                            f"rid={rid} - <@{author}>: (repeating={repeat}) {message} "
                            f"to be sent at <t:{round(datetime.timestamp(send_time))}:f>"
                            f"- requested <t:{round(datetime.timestamp(requested_time))}:f> "
                        )
                        for rid, author, _, message, send_time, requested_time, repeat in reminders
                    ]
                )
            else:
                msg = "No reminders are set"

            embed.add_field(name="Reminders", value=msg)
            await ctx.reply(embed=embed, ephemeral=True, allowed_mentions=mention_only_user)


rems = None


async def setup(bot):
    global rems
    rems = reminders(bot)
    await rems._init()
    await bot.add_cog(rems)


async def teardown(bot):
    if rems is not None:
        await rems._destroy()

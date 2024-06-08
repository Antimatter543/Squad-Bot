import asyncio
import re
from contextlib import suppress
from datetime import datetime, timedelta

import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy import Sequence, select

from bot.database.models import Reminder
from bot.lib.date import now_tz

mention_only_user = discord.AllowedMentions(everyone=False, users=False, roles=False)

cog_name = "reminder"


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
    def seconds_to_string(seconds: int = 0):
        time = timedelta(seconds=seconds)
        mm, ss = divmod(time.seconds, 60)
        hh, mm = divmod(mm, 60)
        return f"{time.days} days, {hh} hours, {mm} minutes, {ss} seconds"


class reminders(commands.GroupCog, name="reminders"):
    class RepeatingReminder:
        def __init__(
            self,
            bot: commands.Bot,
            aid: int,
            cid: int,
            message: str,
            interval: int,
            requested_time: datetime,
            delay: int = 0,
        ) -> None:
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
            try:
                channel = await self.bot.fetch_channel(self.cid)
            except discord.errors.NotFound:
                self.bot.log.error(f"Channel {self.cid} not found")
                return

            now = round(datetime.timestamp(now_tz()))
            then = round(datetime.timestamp(self.requested_time))
            embed = discord.Embed(
                title="Scheduled Reminder",
                description=f"<@{self.aid}>'s repeating reminder\nSent <t:{now}:T> <t:{now}:d>\nReqested: <t:{then}:T> <t:{then}:d>",
            )
            embed.add_field(name="Message", value=f"{self.message}")
            embed.set_footer(text=f"Repeats every: {_time.seconds_to_string(self.interval)}")

            await channel.send(embed=embed, allowed_mentions=mention_only_user)

    create_group = app_commands.Group(name="create", description="create a reminder")

    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.log = bot.log
        self.repeating: dict[int, self.RepeatingReminder] = {}
        self.tasks = []

    async def _init(self):
        """
        Any initialisation code that needs to be run after the bot is ready or
        in async context.

        :raises Exception: if the database is not enabled
        """

        self.log.info(f"Initialised {self.__class__.__name__}")

        if self.bot.db is None:
            raise Exception("This cog requires a database to be enabled.")

        async with self.bot.db.begin() as conn:
            await conn.run_sync(Reminder.__table__.create, checkfirst=True)

        async with self.bot.session as session:
            reminders: Sequence[Reminder] = (await session.scalars(select(Reminder))).all()

            for reminder in reminders:
                rid, aid, cid, msg, send_time, requested_time, repeat = reminder

                now = now_tz()
                if bool(repeat):
                    interval = int((send_time - requested_time).total_seconds())
                    delta = int((now - requested_time).total_seconds())
                    self.repeating[rid] = self.RepeatingReminder(
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
                            asyncio.create_task(
                                self.start_reminder(rid, aid, cid, requested_time, msg, delay=delay, backup=True)
                            )
                        )

    async def _destroy(self):
        for _, reminder in self.repeating.items():
            await reminder.stop()
        for task in self.tasks:
            task.cancel()

    async def start_reminder(
        self,
        rid: int,
        aid: int,
        cid: int,
        requested_time: datetime,
        message: str,
        delay: int = 0,
        backup: bool = False,
    ):
        await asyncio.sleep(delay)
        channel = await self.bot.fetch_channel(cid)

        then = round(datetime.timestamp(requested_time))
        msg = f"<@{aid}>, this is your reminder"
        msg += "(loaded from backup)" if backup else ""
        msg += f"\nReqested <t:{then}:T> <t:{then}:d>"
        msg += f"\nYou wanted to say: {message}"
        await channel.send(msg, allowed_mentions=mention_only_user)
        await self.remove_reminder(aid, rid)

    # region Reminder Control

    async def add_reminder(self, user_id, channel_id, message, send_time, requested_time, repeat=False):
        async with self.bot.session as session:
            reminder = Reminder(
                user_id=user_id,
                channel_id=channel_id,
                message=message,
                send_time=send_time,
                requested_time=requested_time,
                repeat=repeat,
            )
            session.add(reminder)
            await session.commit()
            await session.refresh(reminder)
            return reminder.id

    async def remove_reminder(self, aid: int, rid: int):
        async with self.bot.session as session:
            stmt = select(Reminder).where(Reminder.id == rid).where(Reminder.user_id == aid)
            reminder = (await session.scalars(stmt)).first()
            if reminder is not None:
                await session.delete(reminder)
                await session.commit()
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

        cid = ctx.channel.id if isinstance(ctx, commands.Context) else ctx.channel_id
        aid = author.id
        rid = await self.add_reminder(aid, cid, message, remind_time, now, repeat)
        if not repeat:
            self.tasks.append(asyncio.create_task(self.start_reminder(rid, aid, cid, now, message)))
        else:
            self.repeating[rid] = self.RepeatingReminder(self.bot, aid, cid, message, delta_s, now)
            await self.repeating[rid].start()

    # endregion
    # region Commands

    @create_group.command(
        name="format",
        description="Set a one off reminder (Date Format).",
    )
    @app_commands.describe(
        fmt="Date Format: [d,h,m,s] | e.g. 12h30m or 1d30s or 5m",
        message="Your reminder message.",
    )
    async def create_reminder_fmt(self, interaction: discord.Interaction, fmt: str, message: str):
        await interaction.response.defer(ephemeral=True)
        fmts = {"s": _time.second, "m": _time.minute, "h": _time.hour, "d": _time.day}
        fmt_re = re.compile(r"(\d+d)?(\d+h)?(\d+m)?(\d+s)?")
        matches = re.findall(fmt_re, fmt)

        time_s = 0
        for match in matches:
            for group in match:
                if not group:
                    continue
                time_s += int(group[:-1]) * fmts[group[-1]]
        await self._reminder(interaction, time_s, message)

    @create_group.command(
        name="args",
        description="Set a one off reminder (H,M,S args).",
    )
    @app_commands.describe(
        days="Days.", hours="Hours.", minutes="Minutes.", seconds="Seconds.", message="Your reminder message."
    )
    @app_commands.choices(
        hours=[app_commands.Choice(name=str(i), value=i) for i in range(0, 24)],
        minutes=[app_commands.Choice(name=str(i), value=i) for i in range(0, 56, 5)],
        seconds=[app_commands.Choice(name=str(i), value=i) for i in range(0, 56, 5)],
    )
    @app_commands.checks.bot_has_permissions(send_messages=True)
    async def create_reminder_args(
        self, interaction: discord.Interaction, days: int, hours: int, minutes: int, seconds: int, *, message: str
    ):
        await interaction.response.defer(ephemeral=True)
        time_s = _time.convert_seconds(days=days, hours=hours, minutes=minutes, seconds=seconds)
        await self._reminder(interaction, time_s, message)

    @create_group.command(
        name="repeating",
        description="Reminds you of something (Repeating). 12 Hour minimum",
    )
    @app_commands.describe(days="Days.", hours="Hours.", minutes="Minutes.", message="Your reminder message.")
    @app_commands.choices(
        weeks=[app_commands.Choice(name=str(i), value=i) for i in range(0, 16)],
        hours=[app_commands.Choice(name=str(i), value=i) for i in range(0, 24)],
        minutes=[app_commands.Choice(name=str(i), value=i) for i in range(0, 56, 5)],
    )
    @app_commands.checks.bot_has_permissions(send_messages=True)
    async def create_reminder_repeating(
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

    # TODO: use pagination buttons using the UI
    @app_commands.command(name="show", description="See your reminders")
    @app_commands.checks.bot_has_permissions(send_messages=True)
    async def show_reminders(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        async with self.bot.session as session:
            stmt = select(Reminder).where(Reminder.user_id == interaction.user.id)
            reminders: Sequence[Reminder] = (await session.scalars(stmt)).all()

            embed = discord.Embed(title="Reminders", description=f"{interaction.user.display_name}'s reminders.")
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

    @app_commands.command(
        name="delete",
        description="Delete a repeating reminder",
    )
    @app_commands.describe(rid="Reminder id (see reminders show command).")
    async def delete_reminder(self, interaction: discord.Interaction, rid: int):
        await interaction.response.defer(ephemeral=True)
        await self.remove_reminder(interaction.user.id, rid)
        await interaction.followup.send("Deleted reminder", ephemeral=True)

    # finish interaction on error
    @app_commands.command(
        name="show_all",
        description="See active reminders (Admin Only)",
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def allReminders(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        async with self.bot.session as session:
            reminders: Sequence[Reminder] = (await session.scalars(select(Reminder))).all()
            embed = discord.Embed(title="Reminders", description="All reminders.")
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
            await interaction.followup.send(embed=embed, ephemeral=True, allowed_mentions=mention_only_user)

    # endregion


rems = None


async def setup(bot):
    global rems
    rems = reminders(bot)
    await rems._init()
    await bot.add_cog(rems)


async def teardown(bot):
    if rems is not None:
        await rems._destroy()

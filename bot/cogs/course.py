import re
from datetime import timedelta
from typing import Dict, Optional

import aiohttp
import discord
from bs4 import BeautifulSoup
from discord import app_commands
from discord.ext import commands
from sqlalchemy import Sequence, delete, select

from bot.database.models import CourseChannel, CourseEnrollment
from bot.lib.date import now_tz

cog_name = "course"


class course(commands.Cog):
    course_group = app_commands.Group(name="course", description="Course management")
    enrollments_group = app_commands.Group(name="enrollment", description="Enrollment management")

    # https://ppl.app.uq.edu.au/sites/default/files/DisciplineDescriptor%20table_PPL3%2020%2003%20Course%20Coding%2017Sept2014.pdf
    descriptors = [
        "COMP",
        "COMS",
        "COSC",
        "CSSE",
        "DECO",
        "INFS",
        "MATH",
        "STAT",
        "ENGG",
    ]

    def __init__(self, bot: commands.Bot) -> None:
        super().__init__()
        self.bot = bot
        self.log = bot.log
        self.log.info(f"Loaded {self.__class__.__name__}")
        self.verify_log = {}

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
            await conn.run_sync(CourseChannel.__table__.create, checkfirst=True)
            await conn.run_sync(CourseEnrollment.__table__.create, checkfirst=True)

    def parse_course_code(self, course_code: str) -> tuple[str, int]:
        """
        Parse the course code into its components.

        :param course_code: the course code to parse
        :return: the course code components
        """
        match = re.match(r"([A-Z]{4})([0-9]{4})", course_code)
        if match is None:
            raise ValueError(f"Invalid course code: {course_code}")
        return match.groups()

    async def _get_channel(
        self,
        guild: discord.Guild,
        channel_id: Optional[int] = None,
        channel_name: Optional[str] = None,
        is_category: bool = False,
    ) -> discord.abc.GuildChannel | None:
        """
        Get a channel by id or name.
        If both id and channel_name are provided, the channel found with the id will take priority.
        If neither id nor channel_name are provided or no such channel exists, None will be returned.

        :param channel_id: chnnel id, defaults to None
        :param channel_name: the name of the channel, defaults to None
        :return: channel or None if no channel exists
        """
        if channel_id is not None:
            channel = await guild.fetch_channel(channel_id)
            if channel is not None:
                return channel
        if channel_name is not None:
            channels = guild.text_channels if not is_category else guild.categories
            for channel in channels:
                if channel.name == channel_name:
                    return channel
        return None

    async def get_text_channel(
        self, guild: discord.Guild, *, channel_id: Optional[int] = None, channel_name: Optional[str] = None
    ) -> discord.TextChannel | None:
        """
        Get a channel by id or name.
        If both id and channel_name are provided, the channel found with the id will take priority.
        If neither id nor channel_name are provided or no such channel exists, None will be returned.

        :param channel_id: chnnel id, defaults to None
        :param channel_name: the name of the channel, defaults to None
        :return: channel or None if no channel exists
        """
        return self._get_channel(guild, channel_id, channel_name)

    async def get_category(
        self, guild: discord.Guild, channel_id: Optional[int] = None, channel_name: Optional[str] = None
    ) -> discord.CategoryChannel:
        """
        Get a category by name.

        :param guild: the guild to get the category from
        :param name: the name of the category to get
        :return: the category
        """
        return self._get_channel(guild, channel_id, channel_name, is_category=True)

    async def create_channel(
        self,
        guild: discord.Guild,
        channel_name: str,
        is_category: bool = False,
        overwrites: Optional[Dict[discord.Role, discord.PermissionOverwrite]] = discord.abc.MISSING,
    ) -> discord.abc.GuildChannel:
        """
        Create a channel with the given name in the guild.
        The channel permissions will be sync'd with the category.

        Text channels will be placed in a category with the same name as the course descriptor.
        They will also be ordered by the course number.

        Categories will be ordered by the course descriptor alphabetically.
        By default the category will be hidden from @everyone.

        :param channel_name: the name of the channel
        :return: the newly created channel
        """

        async def add_channel(channel: discord.abc.GuildChannel) -> None:
            async with self.bot.session as session:
                cnl = CourseChannel(
                    channel_id=channel.id,
                    guild_id=channel.guild.id,
                    course_code=channel.name,
                    do_not_reset=False,
                )
                session.add(cnl)
                await session.commit()

        def get_position(channels: list[discord.abc.GuildChannel], channel_name: str) -> int:
            return sorted(channels + [channel_name]).index(channel_name)

        if is_category:
            overwrites = {guild.default_role: discord.PermissionOverwrite(view_channel=False)}
            categories = guild.categories
            course_categories = [cat for cat in categories if cat.name in self.descriptors]
            position = get_position(course_categories, channel_name) + (len(categories) - len(course_categories))
            channel = await guild.create_category(channel_name, overwrites=overwrites, position=position)
            await add_channel(channel)
            return channel

        descriptor, _ = self.parse_course_code(channel_name)
        category = await self.get_category(guild, channel_name=descriptor)
        if category is None:
            category = await self.create_channel(guild, descriptor, is_category=True)
        channels = category.text_channels
        position = get_position(channels, channel_name)
        channel = await guild.create_text_channel(
            channel_name, category=category, position=position, overwrites=overwrites
        )
        # Creating a channel of a specified position will not update the position of other channels to follow suit.
        await channel.edit(position=position)
        await add_channel(channel)
        return channel

    async def delete_channel(self, channel: discord.abc.GuildChannel) -> None:
        async def remove_channel(channel: discord.abc.GuildChannel) -> None:
            async with self.bot.session as session:
                stmt = (
                    delete(CourseChannel)
                    .where(CourseChannel.channel_id == channel.id)
                    .where(CourseChannel.guild_id == channel.guild.id)
                )
                await session.execute(stmt)
                await session.commit()

        if isinstance(channel, discord.TextChannel):
            await remove_channel(channel)
            await channel.delete()
        elif isinstance(channel, discord.CategoryChannel):
            for ch in channel.channels:
                await self.delete_channel(ch)
            await remove_channel(ch)
            await channel.delete()
        else:
            raise ValueError(f"Invalid channel type: {type(channel)}")

    async def get_or_create_course_channel(
        self,
        guild: discord.Guild,
        course_code: str,
    ) -> discord.TextChannel:
        # First check if the channel exists in the database
        course_channel = await self.get_course_code(course_code)
        channel_id = None if course_channel is None else course_channel.channel_id
        channel = await self.get_text_channel(guild, channel_id=channel_id)
        if channel is not None:
            return channel
        # If the channel does not exist, create it
        return await self.create_channel(guild, course_code)

    async def get_course_code(self, course_code: str) -> CourseChannel | None:
        """
        Get the channel from the course code.

        :param course_code: the course code to get
        :return: the course code
        """
        async with self.bot.session as session:
            stmt = select(CourseChannel).where(CourseChannel.course_code == course_code.upper())
            row = (await session.scalars(stmt)).first()
            return row

    def get_text_channel_stats(self, channel: discord.TextChannel) -> discord.Embed:
        """
        Get the number of members in a text channel.

        :param channel: the channel to get the stats from
        :return: the stats
        """
        if channel is None:
            return discord.Embed(title="No such channel exists yet.")
        return discord.Embed(
            title=f"{channel.name}",
            description=f"Members: {len(channel.members)}",
        )

    def get_course_channels(self, guild: discord.Guild) -> list[discord.TextChannel]:
        """
        Get a list of all course channels in the guild.

        :param guild: the guild to get the channels from
        :return: the course channels
        """
        res = []
        for channel in guild.text_channels:
            if channel.category is not None and channel.category.name in self.descriptors:
                res.append(channel)
        return res

    async def verify_course_code(self, course_code: str) -> bool:
        if course_code is None:
            return False
        course = self.verify_log.get(course_code)
        now = now_tz()
        if course is not None and course["time"] > now - timedelta(days=30):
            return course["result"]
        async with aiohttp.ClientSession() as session:
            # site blocks deafult user agent
            headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/"}
            uri = f"https://my.uq.edu.au/programs-courses/course.html?course_code={course_code}"
            async with session.get(uri, headers=headers) as resp:
                if resp.status != 200:
                    return False
                soup = BeautifulSoup(await resp.content, "html.parser")
                verified = soup.find(id="course-notfound") is None
                # keep a log of the verification to avoid spamming the site
                self.verify_log[course_code] = {"result": verified, "time": now}
                return verified

    @course_group.command(name="enrol", description="Enrolling in a course chat allows you to view that channel.")
    @app_commands.describe(
        course_code="The UQ designated course code | e.g. CSSE1001",
    )
    @app_commands.checks.bot_has_permissions(manage_channels=True)
    @app_commands.guild_only()
    async def enrol_course(self, interaction: discord.Interaction, course_code: str):
        await interaction.response.defer(ephemeral=True)
        user = interaction.user
        guild = interaction.guild
        code = course_code.upper()
        if not await self.verify_course_code(code):
            await interaction.followup.send(
                f"Invalid course code: {course_code}",
                ephemeral=True,
                delete_after=30,
                mention_author=False,
            )
            return
        descriptor, _ = self.parse_course_code(course_code)
        if descriptor not in self.descriptors:
            await interaction.followup.send(
                f"Invalid course descriptor: {descriptor}. Must be one of {', '.join(self.descriptors)}.",
                ephemeral=True,
                delete_after=30,
                mention_author=False,
            )
            return
        channel = await self.get_or_create_course_channel(guild, code)
        channel.set_permissions(user, overwrite=discord.PermissionOverwrite(view_channel=True))
        with self.bot.session as session:
            enrollment = CourseEnrollment(
                user_id=user.id,
                channel_id=channel.id,
                guild_id=guild.id,
            )
            session.add(enrollment)
            await session.commit()
        await interaction.followup.send(
            f"Successfully enrolled in {course_code}",
            embed=self.get_text_channel_stats(channel),
            ephemeral=True,
            delete_after=30,
            mention_author=False,
        )

    @course_group.command(name="drop", description="Dropping a course chat removes your access to that channel.")
    @app_commands.describe(
        course_code="The UQ designated course code | e.g. CSSE1001",
    )
    @app_commands.checks.bot_has_permissions(manage_channels=True)
    @app_commands.guild_only()
    async def drop_course(self, interaction: discord.Interaction, course_code: str):
        await interaction.response.defer(ephemeral=True)
        user = interaction.user
        guild = interaction.guild
        code = course_code.upper()
        if not await self.verify_course_code(code):
            await interaction.followup.send(
                f"Invalid course code: {course_code}",
                ephemeral=True,
                delete_after=30,
                mention_author=False,
            )
            return
        channel = await self.get_or_create_course_channel(guild, code)
        channel.set_permissions(user, overwrite=None)
        with self.bot.session as session:
            stmt = (
                delete(CourseEnrollment)
                .where(CourseEnrollment.user_id == user.id)
                .where(CourseEnrollment.channel_id == channel.id)
                .where(CourseEnrollment.guild_id == guild.id)
            )
            await session.execute(stmt)
            await session.commit()
        await interaction.followup.send(
            f"Successfully dropped {course_code}",
            embed=self.get_text_channel_stats(channel),
            ephemeral=True,
            delete_after=30,
            mention_author=False,
        )

    @course_group.command(name="show", description="Show how many members are in a course chat.")
    @app_commands.describe(
        course_code="The UQ designated course code | e.g. CSSE1001",
    )
    @app_commands.checks.bot_has_permissions(manage_channels=True)
    @app_commands.guild_only()
    async def show_course(self, interaction: discord.Interaction, course_code: str):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        code = course_code.upper()
        if not await self.verify_course_code(code):
            await interaction.followup.send(
                f"Invalid course code: {course_code}",
                ephemeral=True,
                delete_after=30,
                mention_author=False,
            )
            return
        channel = await self.get_text_channel(guild, channel_name=code)
        await interaction.followup.send(
            embed=self.get_text_channel_stats(channel),
            ephemeral=True,
            delete_after=30,
            mention_author=False,
        )

    async def reset_course(self, channel: discord.TextChannel) -> None:
        overwrites = channel.overwrites
        await self.delete_channel(channel)
        await self.create_channel(channel.guild, channel.name, overwrites=overwrites)

    @course_group.command(name="reset", description="(Admin Only) Remove all messages from a course chat.")
    @app_commands.guild_only()
    @app_commands.checks.bot_has_permissions(manage_channels=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def reset_course_command(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)
        if channel is None:
            await interaction.followup.send(
                "No such channel exists yet.",
                ephemeral=True,
                delete_after=30,
                mention_author=False,
            )
            return
        self.reset_course(channel)
        await interaction.followup.send(
            f"Successfully reset {channel.name}",
            ephemeral=True,
            delete_after=30,
            mention_author=False,
        )

    @course_group.command(name="reset_all", description="(Admin Only) Remove all messages from all course chats.")
    @app_commands.guild_only()
    @app_commands.checks.bot_has_permissions(manage_channels=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def reset_all_courses(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        async with self.bot.session as session:
            stmt = select(CourseChannel).where(CourseChannel.guild_id == guild.id)
            rows: Sequence[CourseChannel] = (await session.scalars(stmt)).all()
            for row in rows:
                if row.do_not_reset:
                    continue
                channel = await self.get_text_channel(guild, channel_id=row.channel_id)
                if channel is not None:
                    await self.reset_course(channel)

        await interaction.followup.send(
            "Successfully reset all course chats",
            ephemeral=True,
            delete_after=30,
            mention_author=False,
        )

    @course_group.command(
        name="reset_exception", description="(Admin Only) Make a course as an exception to the reset_all command."
    )
    @app_commands.guild_only()
    @app_commands.checks.bot_has_permissions(manage_channels=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def reset_exception(self, interaction: discord.Interaction, channel: discord.TextChannel, exception: bool):
        await interaction.response.defer(ephemeral=True)
        async with self.bot.session as session:
            stmt = (
                select(CourseChannel)
                .where(CourseChannel.channel_id == channel.id)
                .where(CourseChannel.guild_id == channel.guild.id)
            )
            row = (await session.scalars(stmt)).first()
            if row is None:
                await interaction.followup.send(
                    "No such channel exists yet.",
                    ephemeral=True,
                    delete_after=30,
                    mention_author=False,
                )
                return
            row.do_not_reset = exception
            await session.commit()
        await interaction.followup.send(
            f"Successfully added {channel.name} to the reset exception list",
            ephemeral=True,
            delete_after=30,
            mention_author=False,
        )

    @course_group.command(name="sync", description="(Admin Only) Sync the current course channels with the database.")
    @app_commands.guild_only()
    @app_commands.checks.bot_has_permissions(manage_channels=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def sync_courses(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        async with self.bot.session as session:
            stmt = select(CourseChannel).where(CourseChannel.guild_id == guild.id)
            channels_db: Sequence[CourseChannel] = (await session.scalars(stmt)).all()
            db_channel_ids = []
            # manage old channels
            for channel in channels_db:
                channel = await self.get_text_channel(guild, channel_id=channel.channel_id)
                # delete old channels
                if channel is None:
                    await session.delete(channel)
                    continue
                db_channel_ids.append(channel.id)
                if channel.name != channel.course_code:
                    channel.course_code = channel.name
                enroll_stmt = (
                    select(CourseEnrollment)
                    .where(CourseEnrollment.channel_id == channel.id)
                    .where(CourseEnrollment.guild_id == guild.id)
                )
                enrollments_db: Sequence[CourseEnrollment] = (await session.scalars(enroll_stmt)).all()
                channel_enrollment_ids = [user.id for user in channel.members]

                db_enrollment_ids = []
                # remove old enrollments
                for enrollment in enrollments_db:
                    if enrollment.user_id not in channel_enrollment_ids:
                        await session.delete(enrollment)
                    else:
                        db_enrollment_ids.append(enrollment.user_id)
                # add new enrollments
                for uid in channel_enrollment_ids:
                    if uid not in db_enrollment_ids:
                        enrollment = CourseEnrollment(
                            user_id=uid,
                            channel_id=channel.id,
                            guild_id=guild.id,
                        )
                        session.add(enrollment)
            # add new channels
            channels = self.get_course_channels(guild)
            for channel in channels:
                if len(channel.members) == 0:
                    continue
                if channel.id not in db_channel_ids:
                    channel = CourseChannel(
                        channel_id=channel.id,
                        guild_id=guild.id,
                        course_code=channel.name,
                        do_not_reset=False,
                    )
                    session.add(channel)
                    for member in channel.members:
                        enrollment = CourseEnrollment(
                            user_id=member.id,
                            channel_id=channel.id,
                            guild_id=guild.id,
                        )
                        session.add(enrollment)
            await session.commit()
        await interaction.followup.send(
            "Successfully synced all course channels",
            ephemeral=True,
            delete_after=30,
            mention_author=False,
        )

    @course_group.command(name="clean", description="(Admin Only) Remove any courses that have no enrollment.")
    @app_commands.guild_only()
    @app_commands.checks.bot_has_permissions(manage_channels=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def clean_courses(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        async with self.bot.session as session:
            for channel in self.get_course_channels(guild):
                stmt = (
                    select(CourseEnrollment)
                    .where(CourseEnrollment.channel_id == channel.id)
                    .where(CourseEnrollment.guild_id == guild.id)
                )
                enrollments: Sequence[CourseEnrollment] = (await session.scalars(stmt)).all()
                if len(enrollments) == 0:
                    await self.delete_channel(channel)

    @enrollments_group.command(name="purge", description="(Admin Only) Remove all enrollments for user.")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def purge_enrollments(self, interaction: discord.Interaction, user: Optional[discord.User] = None) -> None:
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        if user is None:
            user = interaction.user
        async with self.bot.session as session:
            stmt = (
                delete(CourseEnrollment)
                .where(CourseEnrollment.user_id == user.id)
                .where(CourseEnrollment.guild_id == guild.id)
            )
            await session.execute(stmt)
            await session.commit()
        await interaction.followup.send(
            f"Successfully removed all enrollments for {user} for {guild.name}",
            ephemeral=True,
            delete_after=30,
            mention_author=False,
        )

    @enrollments_group.command(name="list", description="(Admin Only) List all enrollments for user.")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def list_enrollments(self, interaction: discord.Interaction, user: Optional[discord.User] = None) -> None:
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        if user is None:
            user = interaction.user
        async with self.bot.session as session:
            stmt = (
                select(CourseEnrollment)
                .where(CourseEnrollment.user_id == user.id)
                .where(CourseEnrollment.guild_id == guild.id)
            )
            enrollments: Sequence[CourseEnrollment] = (await session.scalars(stmt)).all()
        embed = discord.Embed(title=f"{user} enrollments")
        for enrollment in enrollments:
            channel = await self.get_text_channel(guild, channel_id=enrollment.channel_id)
            embed.add_field(name=channel.name, value=f"ID: {channel.id}", inline=False)
        await interaction.followup.send(
            embed=embed,
            ephemeral=True,
            delete_after=30,
            mention_author=False,
        )


async def setup(bot):
    cog = course(bot)
    await cog._init()
    await bot.add_cog(cog)


async def teardown(bot):
    pass

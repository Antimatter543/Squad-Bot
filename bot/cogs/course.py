import re
from datetime import timedelta
from typing import Dict, Optional

import aiohttp
import discord
from bs4 import BeautifulSoup
from discord import app_commands
from discord.ext import commands
from sqlalchemy import Sequence, delete, select

from bot.database.models import CourseChannel, CourseConfig, CourseEnrollment, Course
from bot.lib.date import now_tz

cog_name = "course"


class course(commands.Cog):
    class Config:
        def __init__(self) -> None:
            self.auto_delete = True
            self.auto_delete_ignore_admins = False
            self.course_codes = []

        @classmethod
        async def from_row(cls, bot: commands.Bot, row: CourseConfig, codes: list[str] = None):
            """
            Create a new Config object from a row in the database

            :param commands.Bot bot: the bot instance
            :param CourseConfig row: the stored DB config
            :raises ValueError: if the row is None
            """
            if row is None:
                raise ValueError("Could not find a row in the database for this guild.")
            obj = cls()
            try:
                guild: discord.Guild | None = await bot.fetch_guild(row.guild_id)
                if guild is None:
                    return obj
                obj.auto_delete = row.auto_delete
                obj.auto_delete_ignore_admins = row.auto_delete_ignore_admins
            except discord.Forbidden:
                bot.log.warning(f"Could not find a channel or role for guild {row.guild_id}")
                pass
            if codes is not None:
                obj.course_codes = codes
            return obj

    course_group = app_commands.Group(name="course", description="Course management")
    enrollments_group = app_commands.Group(name="enrollment", description="Enrollment management")

    # https://ppl.app.uq.edu.au/sites/default/files/DisciplineDescriptor%20table_PPL3%2020%2003%20Course%20Coding%2017Sept2014.pdf
    # descriptors = [
    #     "COMP",
    #     "COMS",
    #     "COSC",
    #     "CSSE",
    #     "CYBR",
    #     "DECO",
    #     "INFS",
    #     "MATH",
    #     "STAT",
    #     "ENGG",
    # ]

    def __init__(self, bot: commands.Bot) -> None:
        super().__init__()
        self.bot = bot
        self.log = bot.log
        self.log.info(f"Loaded {self.__class__.__name__}")
        self.verify_log = {}

        bot.modules[cog_name] = {}
        for guild in bot.guilds:
            bot.modules[cog_name][guild.id] = self.Config()

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
            await conn.run_sync(CourseConfig.__table__.create, checkfirst=True)
            await conn.run_sync(Course.__table__.create, checkfirst=True)

        for guild in self.bot.guilds:
            await self.enroll(guild.id)

    async def enroll(self, guild_id):
        async with self.bot.session as session:
            self.log.info(f"{cog_name} - Enrolling guild {guild_id}")
            row = await session.get(CourseConfig, guild_id)
            if row is None:
                return
            all_codes = (await session.scalars(select(Course))).all()
            codes = [code.course_code for code in all_codes]
            self.bot.modules[cog_name][guild_id] = await self.Config.from_row(self.bot, row, codes)

    def format_channel_name(self, name: str, is_category=False) -> str:
        """
        Format the channel name to be uppercase if it is a category.
        else lowercase
        """
        return name.upper() if is_category else name.lower()

    def parse_course_code(self, course_code: str, *, allow_category=False) -> tuple[str, int]:
        """
        Parse the course code into its components.

        :param course_code: the course code to parse
        :return: the course code components
        """
        match = re.match(r"([A-Za-z]{4})([0-9]{4})", course_code)
        if allow_category and match is None:
            match = re.match(r"([A-Za-z]{4})", course_code)
        if match is None:
            raise commands.ArgumentParsingError(f"Invalid course code: {course_code}")
        if allow_category:
            return match.group(1), 0
        code, number = match.groups()
        return self.format_channel_name(code, is_category=True), int(number)

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
            try:
                channel = await guild.fetch_channel(channel_id)
                return channel
            except discord.errors.NotFound:
                return None
        if channel_name is not None:
            channel_name = self.format_channel_name(channel_name, is_category)
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
        return await self._get_channel(guild, channel_id, channel_name)

    async def get_category(
        self, guild: discord.Guild, channel_id: Optional[int] = None, channel_name: Optional[str] = None
    ) -> discord.CategoryChannel:
        """
        Get a category by name.

        :param guild: the guild to get the category from
        :param name: the name of the category to get
        :return: the category
        """
        return await self._get_channel(guild, channel_id, channel_name, is_category=True)

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
            names = [ch.name for ch in channels]
            return sorted(names + [channel_name]).index(channel_name)

        config = self.bot.modules[cog_name].get(guild.id)
        
        channel_name = self.format_channel_name(channel_name, is_category)
        if is_category:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                self.bot.user: discord.PermissionOverwrite(view_channel=True),
            }
            categories = guild.categories
            course_categories = [cat for cat in categories if cat.name in config.course_codes]
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
            await remove_channel(channel)
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
        # check if it exists by name
        channel = await self.get_text_channel(guild, channel_name=course_code)
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
        code = self.format_channel_name(course_code)
        async with self.bot.session as session:
            stmt = select(CourseChannel).where(CourseChannel.course_code == code)
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
        members = [
            member
            for member in channel.members
            if member.bot is False and member.guild_permissions.administrator is False
        ]
        return discord.Embed(
            title=f"{channel.name}",
            description=f"Members: {len(members)}",
        )

    def get_course_channels(self, guild: discord.Guild) -> list[discord.TextChannel]:
        """
        Get a list of all course channels in the guild.

        :param guild: the guild to get the channels from
        :return: the course channels
        """
        res = []
        config = self.bot.modules[cog_name].get(guild.id)
        
        for channel in guild.text_channels:
            if channel.category is not None and channel.category.name in config.course_codes:
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
            # site blocks default user agent
            headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/"}
            uri = f"https://my.uq.edu.au/programs-courses/course.html?course_code={course_code}"
            async with session.get(uri, headers=headers) as resp:
                if resp.status != 200:
                    return False
                soup = BeautifulSoup(await resp.content.read(), "html.parser")
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
        code = self.format_channel_name(course_code)
        if not await self.verify_course_code(code):
            await interaction.followup.send(
                f"Invalid course code: {code}",
                ephemeral=True,
            )
            return
        descriptor, _ = self.parse_course_code(code)
        config = self.bot.modules[cog_name].get(guild.id)
        if descriptor not in config.course_codes:
            await interaction.followup.send(
                f"Cannot enroll in that course type in this server: {descriptor}. Must be one of {', '.join(config.course_codes)}.",
                ephemeral=True,
            )
            return
        channel = await self.get_or_create_course_channel(guild, code)
        if user in channel.members:
            await interaction.followup.send(
                f"You are already enrolled in {code}",
                ephemeral=True,
            )
            return
        await channel.set_permissions(user, overwrite=discord.PermissionOverwrite(view_channel=True))
        async with self.bot.session as session:
            enrollment = CourseEnrollment(
                user_id=user.id,
                channel_id=channel.id,
                guild_id=guild.id,
                course_code=channel.name,
            )
            session.add(enrollment)
            await session.commit()
        await interaction.followup.send(
            f"Successfully enrolled in {code}",
            embed=self.get_text_channel_stats(channel),
            ephemeral=True,
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
        code = self.format_channel_name(course_code)
        if not await self.verify_course_code(code):
            await interaction.followup.send(
                f"Invalid course code: {code}",
                ephemeral=True,
            )
            return
        channel = await self.get_text_channel(guild, channel_name=code)
        if channel is None:
            await interaction.followup.send(
                f"No such channel exists yet.",
                ephemeral=True,
            )
            return
        if user not in channel.members:
            await interaction.followup.send(
                f"You are not enrolled in {code}",
                ephemeral=True,
            )
            return
        await channel.set_permissions(user, overwrite=None)
        # check if we need to auto delete the channel
        config = self.bot.modules[cog_name].get(guild.id)
        if config is not None and config.auto_delete:
            members = [member for member in channel.members if member.bot is False]
            if config.auto_delete_ignore_admins is True:
                members = [member for member in members if member.guild_permissions.administrator is False]
            if len(members) == 0:
                await self.delete_channel(channel)
            # check if the category is empty and delete it if needed
            descriptor, _ = self.parse_course_code(code)
            category = await self.get_category(guild, channel_name=descriptor)
            if len(category.text_channels) == 0:
                await self.delete_channel(category)
        async with self.bot.session as session:
            stmt = (
                delete(CourseEnrollment)
                .where(CourseEnrollment.user_id == user.id)
                .where(CourseEnrollment.channel_id == channel.id)
                .where(CourseEnrollment.guild_id == guild.id)
            )
            await session.execute(stmt)
            await session.commit()
        await interaction.followup.send(
            f"Successfully dropped {code}",
            embed=self.get_text_channel_stats(channel),
            ephemeral=True,
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
        code = self.format_channel_name(course_code)
        if not await self.verify_course_code(code):
            await interaction.followup.send(
                f"Invalid course code: {code}",
                ephemeral=True,
            )
            return
        channel = await self.get_text_channel(guild, channel_name=code)
        await interaction.followup.send(
            embed=self.get_text_channel_stats(channel),
            ephemeral=True,
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
            )
            return
        self.reset_course(channel)
        await interaction.followup.send(
            f"Successfully reset {channel.name}",
            ephemeral=True,
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
                )
                return
            row.do_not_reset = exception
            await session.commit()
        await interaction.followup.send(
            f"Successfully added {channel.name} to the reset exception list",
            ephemeral=True,
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
            for channel_db in channels_db:
                channel = await self.get_text_channel(guild, channel_id=channel_db.channel_id)
                # delete old channels
                if channel is None:
                    await session.delete(channel_db)
                    continue
                db_channel_ids.append(channel.id)
                if channel_db.course_code != channel.name:
                    channel_db.course_code = channel.name
                enroll_stmt = (
                    select(CourseEnrollment)
                    .where(CourseEnrollment.channel_id == channel.id)
                    .where(CourseEnrollment.guild_id == guild.id)
                )
                enrollments_db: Sequence[CourseEnrollment] = (await session.scalars(enroll_stmt)).all()
                channel_enrollment_ids = [
                    user.id for user in channel.members if not user.bot and not user.guild_permissions.administrator
                ]

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
                            course_code=channel.name,
                        )
                        session.add(enrollment)
            # add new channels
            channels = self.get_course_channels(guild)
            config = self.bot.modules[cog_name].get(guild.id)
            channels += [channel for channel in guild.categories if channel.name in config.course_codes]
            for channel in channels:
                if channel.id not in db_channel_ids:
                    channel_db = CourseChannel(
                        channel_id=channel.id,
                        guild_id=guild.id,
                        course_code=channel.name,
                        do_not_reset=False,
                    )
                    session.add(channel_db)
                    if isinstance(channel, discord.TextChannel):
                        for member in channel.members:
                            if member.bot or member.guild_permissions.administrator:
                                continue
                            enrollment = CourseEnrollment(
                                user_id=member.id,
                                channel_id=channel.id,
                                guild_id=guild.id,
                                course_code=channel.name,
                            )
                            session.add(enrollment)
            await session.commit()
        await interaction.followup.send(
            "Successfully synced all course channels",
            ephemeral=True,
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
        await interaction.followup.send(
            "Successfully cleaned all course channels",
            ephemeral=True,
        )

    @course_group.command(name="delete", description="(Admin Only) Remove a course chat.")
    @app_commands.guild_only()
    @app_commands.checks.bot_has_permissions(manage_channels=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def delete_courses(self, interaction: discord.Interaction, channel: discord.abc.GuildChannel) -> None:
        await interaction.response.defer(ephemeral=True)
        descriptor, _ = self.parse_course_code(channel.name, allow_category=True)
        config = self.bot.modules[cog_name].get(interaction.guild.id)
        if descriptor not in config.course_codes:
            await interaction.followup.send(f"Cannot use this command to delete non-course channels.", ephemeral=True)
            return
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
            f"Successfully removed all enrollments for {user} for {guild.name}", ephemeral=True
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
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    cog = course(bot)
    await cog._init()
    await bot.add_cog(cog)


async def teardown(bot):
    pass

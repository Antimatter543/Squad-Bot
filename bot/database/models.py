from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Identity, backref, relationship
from sqlalchemy.orm import Mapped, mapped_column

from bot.database import Base

# statistics.py


class Screams(Base):
    __tablename__ = "dc_screams"
    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    sc_total: Mapped[int]
    sc_streak: Mapped[int]
    sc_best_streak: Mapped[int]
    sc_daily: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    sc_streak_keeper: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    def __repr__(self):
        return (
            f"<Screams("
            f"user_id={self.user_id},"
            f"sc_total={self.sc_total},"
            f"sc_streak={self.sc_streak},"
            f"sc_best_streak={self.sc_best_streak},"
            f"sc_daily={self.sc_daily},"
            f"sc_streak_keeper={self.sc_streak_keeper}"
            ")>"
        )


class StatisticsConfig(Base):
    __tablename__ = "dc_statistics_config"
    guild_id = mapped_column(BigInteger, primary_key=True)
    regexp_primary: Mapped[Optional[str]]
    regexp_secondary: Mapped[Optional[str]]
    channel_id: Mapped[Optional[int]] = mapped_column(BigInteger)
    minor_threshold: Mapped[Optional[int]]
    major_threshold: Mapped[Optional[int]]
    minor_role_id: Mapped[Optional[int]] = mapped_column(BigInteger)
    major_role_id: Mapped[Optional[int]] = mapped_column(BigInteger)


# reminder.py


class Reminder(Base):
    __tablename__ = "dc_reminders"
    id: Mapped[int] = mapped_column(Identity(start=1, cycle=True), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger)
    channel_id: Mapped[int] = mapped_column(BigInteger)
    message: Mapped[str]
    send_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    requested_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    repeat: Mapped[bool]

    def __repr__(self):
        return (
            f"<Reminder("
            f"id={self.id},"
            f"user_id={self.user_id},"
            f"channel_id={self.channel_id},"
            f"message={self.message},"
            f"send_time={self.send_time},"
            f"requested_time={self.requested_time},"
            f"repeat={self.repeat}"
            ")>"
        )

    def __iter__(self):
        return iter(
            (self.id, self.user_id, self.channel_id, self.message, self.send_time, self.requested_time, self.repeat)
        )


# courses.py


class CourseChannel(Base):
    __tablename__ = "dc_course_channels"
    channel_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    course_code: Mapped[str]
    do_not_reset: Mapped[bool]

    def __repr__(self):
        return (
            f"<CourseChannel("
            f"channel_id={self.channel_id},"
            f"guild_id={self.guild_id},"
            f"course_code={self.course_code},"
            f"do_not_reset={self.do_not_reset}"
            ")>"
        )


class CourseEnrollment(Base):
    __tablename__ = "dc_course_enrollments"
    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    channel_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("dc_course_channels.channel_id"), primary_key=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    channel = relationship(
        "CourseChannel",
        foreign_keys=[channel_id, guild_id],
        backref=backref("dc_course_enrollments", cascade="all, delete-orphan"),
    )

    def __repr__(self):
        return (
            f"<CourseEnrollment("
            f"user_id={self.user_id},"
            f"channel_id={self.channel_id},"
            f"guild_id={self.guild_id}"
            ")>"
        )

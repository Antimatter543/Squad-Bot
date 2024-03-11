from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Identity
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

    def __repr__(self):
        return f"<Screams(user_id={self.user_id}, sc_total={self.sc_total}, sc_streak={self.sc_streak}, sc_best_streak={self.sc_best_streak}, sc_daily={self.sc_daily})>"


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
        return f"<Reminder(id={self.id}, user_id={self.user_id}, channel_id={self.channel_id}, message={self.message}, send_time={self.send_time}, requested_time={self.requested_time}, repeat={self.repeat})>"

    def __iter__(self):
        return iter(
            (self.id, self.user_id, self.channel_id, self.message, self.send_time, self.requested_time, self.repeat)
        )

from datetime import datetime, timedelta

import pytz


def get_tz() -> pytz.timezone:
    return pytz.timezone("Australia/Brisbane")


def epoch() -> datetime:
    """
    Returns the epoch date time

    :return: date time (epoch)
    """
    return datetime(1970, 1, 1, tzinfo=get_tz())


def now_tz() -> datetime:
    """
    Returns a datetime formated to Australia/Brisbane TZ

    :return: date time (region based)
    """
    return datetime.now(tz=get_tz())

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


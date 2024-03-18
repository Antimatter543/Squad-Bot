from datetime import datetime

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

from datetime import datetime

import pytz


def get_tz():
    return pytz.timezone("Australia/Brisbane")


def now_tz() -> datetime:
    """
    Returns a datetime formated to Australia/Brisbane TZ

    :return: date time (region based)
    """
    return datetime.now(tz=get_tz())

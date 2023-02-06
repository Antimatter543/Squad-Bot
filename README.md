# UQCSC-Bot
[![Python Version 3.10](https://img.shields.io/badge/python-3.10-blue.svg?logo=python&logoColor=yellow)](https://www.python.org/downloads/release/python-3100/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=flat)](https://github.com/Caleb-Wishart/Squad-Bot/pulls)
![Works on my machine](https://img.shields.io/badge/WORKS%20ON-MY%20MACHINE-red)

A somewhat complete discord bot template with example cogs that uses a Postgresql server as a storage mechanism.

Primarly used for the [UQCS Courses Discord Server](https://discord.gg/JpjaB2FNdW).

## Contributing

This repository uses the [Black code style](https://black.readthedocs.io/en/stable/) to format python files. \
The use of the [flake8](https://pypi.org/project/flake8/) and [isort](https://pypi.org/project/isort/) is highly prefered.

See [requirements-dev.txt](./bot/requirements-dev.txt).

## Default Features
 - Main bot
   - Loading a configuration from an object or dictionary
   - File logging
   - PSQL Database connection
   - Cogs manager
 - Cogs
   - Administrative
     - Add or remove privileged roles
     - Clear message
   - General
     - Fortune
     - Ping
     - Decide
   - Statistics
     - Determine how many times a particular message has been sent to a channel
     - Role based rewards
     - Leaderboard scoring system
     - Crash Safe
   - Reminders
     - Create / Delete repeating or once off reminders
     - Crash Safe

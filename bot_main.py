# bot_main.py
### IMPORT ###
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv, find_dotenv
from roles import admin_roles, elevated_roles
import logging
import asyncio
### TOKENS ###
# load the env files
load_dotenv('.env')
BOT_TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID  = os.getenv("DISCORD_GUILD")
# check token
if BOT_TOKEN == None:
    print('Invalid .env Token')
    exit()

logging.basicConfig(filename='bot.log', level=logging.INFO)

### CLIENT ###

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.members = True

client = commands.Bot(command_prefix='.cs ',intents=intents)

### COMMANDS ###
# on bot connection
@client.event
async def on_ready():
    await client.change_presence(status=discord.Status.online,
            activity=discord.Activity(type=discord.ActivityType.listening, name='.cs help'))

    for guild in client.guilds:
        logging.info(f'{client.user} is connected to the following guild:\n {guild.name} (id: {guild.id})')  # will not print anything
        if guild.id == GUILD_ID:
            break
        print(f'{client.user} is connected to the following guild:\n {guild.name} (id: {guild.id})')

@client.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send('Invalid command used.')
    elif isinstance(error, commands.MissingAnyRole):
        await ctx.send('Insufficent permission')
    # handled in private error functions
    elif isinstance(error,commands.MissingRequiredArgument):
        pass
    elif isinstance(error, commands.ExtensionNotLoaded):
        await ctx.send('Extension has not been loaded')
    else:
        await ctx.send(f'An error occured, {error}')

@client.command(
        brief='Loads a command extention',
        description='Loads a command extention\nUsage: load [extention name]'
        )
@commands.has_any_role(*admin_roles)
async def load(ctx, extension):
    await client.load_extension(f'cogs.{extension}')
    await ctx.send(f'Loaded {str(extension)}!')

@client.command(
        brief='Unloads a command extention',
        description='Unloads a command extention\nUsage: unload [extention name]'
        )
@commands.has_any_role(*admin_roles)
async def unload(ctx, extension):
    await client.unload_extension(f'cogs.{extension}')
    await ctx.send(f'Unloaded {str(extension)}!')

@client.command(
        brief='Reoads a command extention',
        description='Reloads a command extention\nUsage: reload [extention name]'
        )
@commands.has_any_role(*admin_roles)
async def reload(ctx, extension):
    await client.reload_extension(f'cogs.{extension}')
    if extension == 'reminder_commads':
        await ctx.send(f'Did you remember to close all currently active reminders, if not restarting code is required')
    await ctx.send(f'Reloaded {str(extension)}!')



async def load_extensions():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            # cut off the .py from the file name
            await client.load_extension(f"cogs.{filename[:-3]}")

async def main():
    async with client:
        await load_extensions()
        await client.start(BOT_TOKEN)

# run
asyncio.run(main())

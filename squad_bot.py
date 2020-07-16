# squad_bot.py

import os
import discord
from dotenv import load_dotenv

import bot_settings as setting

# load the env files
load_dotenv()
# establish reference to client
client = discord.Client()
# get private token
BOT_TOKEN = os.getenv("BOT_TOKEN")
GUILD_ID  = os.getenv("DISCORD_GUILD")

# check token
if BOT_TOKEN == None:
    print('Invalid .env Token')
    exit()

# online feedback
@client.event
async def on_ready():
    for guild in client.guilds:
        if guild.id == GUILD_ID:
            break
    print(
        f'{client.user} is connected to the following guild:\n'
        f'{guild.name} (id: {guild.id})'
    )

# commands
@client.event
async def on_message(message):
    # ignore messages written by self
    if message.author == client.user:
        return

    # reply to command *hello
    if message.content == '*ping':
        if check_Perms(message.author):
            await message.channel.send('Pong!')
        else:
            await message.channel.send('You are not permitted to run this command')

    # close bot
    if message.content == '*shutdown':
        if dev_Perms(message.author):
            await message.channel.send('Goodbye!')
            print(f'{client.user} shutting down!')
            exit()
        else:
            await message.channel.send('You are not permitted to run this command')

    # remove 
    # dev 
    if message.content.startswith('*eval'):
        if dev_Perms(message.author):
            res = eval(message.content[5:])
            await message.channel.send(res)
        else:
            await message.channel.send('You are not permitted to run this command')

    if message.content == '*help':
        if check_Perms(message.author):
            await message.channel.send(setting.help_text)
        else:
            await message.channel.send('You are not permitted to run this command')

def check_Perms(member):
    member_roles = [role.name for role in member.roles]
    for role in setting.elevated_roles_name:
        if role in member_roles:
            return True
    return False

def dev_Perms(member):
    member_roles = [role.name for role in member.roles]
    for role in setting.dev_role:
        if role in member_roles:
            return True
    return False
    
# connect to discord
client.run(BOT_TOKEN)
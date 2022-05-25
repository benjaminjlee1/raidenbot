# bot.py

import os
import discord
import json
import pylast
import datetime
# import interactions

from dotenv import load_dotenv
from discord.ext import commands
from discord.commands import Option
from datetime import date
# from discord_slash import SlashCommand, SlashContext
# from discord_slash.utils.manage_commands import create_choice, create_option

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
KEY = os.getenv('API_KEY')
SECRET = os.getenv('API_SECRET')
PREFIX = ";"

guildFile = open('guilds.json')
guildDict = json.load(guildFile)
GUILD_IDS = guildDict["ids"]
guildFile.close()

userFile = open('usernames.json')
fileDict = json.load(userFile)
userFile.close()

network = pylast.LastFMNetwork(
    api_key = KEY,
    api_secret = SECRET
)


# Functions

def get_user_embed(user):
    discID = str(user.id)
    lastUser = network.get_user(fileDict[discID])

    birth = date.fromtimestamp(int(lastUser.get_registered()))
    # TODO: consider timezone, DST

    embed = discord.Embed(
        title="Last.fm Profile",
        description=f"[{lastUser.get_name()}]({lastUser.get_url()})",
        color=user.color
    )
    embed.set_author(name=user.display_name, icon_url=user.display_avatar)
    embed.add_field(name="Account Created", value=birth.strftime("%b %d, %Y"))
    embed.add_field(name="\u200B", value="\u200B", inline=True)
    embed.add_field(name="Total Plays", value=lastUser.get_playcount())
    i = lastUser.get_image()
    if i:
        embed.set_thumbnail(url=i)

    return embed

def get_id_from_mention(mention):
    id = mention[2:-1]
    if id[0] == '!':
        id = id[1:]
    return id


# Method 5: Pycord
intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix=PREFIX, intents=intents)
# user.color breaks with the intent if I do intents=discord.Intents(members=True)

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')

@bot.command()
async def ping(ctx):
    await ctx.send("pong")

@bot.slash_command(guild_ids=GUILD_IDS)
async def l(ctx):
    await ctx.respond("Hello!")

# Set username
@bot.slash_command(
    guild_ids=GUILD_IDS,
    description="Set Last.fm username"
)
async def setuser(ctx, username: Option(str, "Enter your Last.fm username")):
    author = ctx.author
    discUser = author.mention
    discID = str(author.id)
    
    fileDict[discID] = username

    with open('usernames.json', 'w') as f:
        json.dump(fileDict, f, indent=4, ensure_ascii=False)
        # f.close()

    # TODO: check if lastfm account exists

    ans = f"{discUser} has been set to: `{username}`"
    await ctx.respond(ans, embed=get_user_embed(ctx.author))

# User info
@bot.slash_command(
    guild_ids=GUILD_IDS,
    description="Display Last.fm profile info"
)
async def profile(ctx, mention: Option(str, "Enter @user", required=False)):
    if mention:
        id = get_id_from_mention(mention)
        user = await ctx.guild.fetch_member(id)
    else:
        user = ctx.author

    if str(user.id) in fileDict.keys():
        await ctx.respond(embed=get_user_embed(user))
    else:
        await ctx.respond("User has not set Last.fm account")
 
# Now playing
@bot.slash_command(
    guild_ids=GUILD_IDS,
    description="Display your currently playing song"
)
async def np(ctx):
    author = ctx.author
    discID = str(author.id)
    if discID not in fileDict.keys():
        await ctx.respond("User has not set Last.fm account")
        return

    lastUser = fileDict[discID]
    user = network.get_user(lastUser)

    embed = discord.Embed(
        title="Now Playing:",
        color=author.color
    )
    embed.set_author(name=author.display_name, icon_url=author.display_avatar)

    track = user.get_now_playing()

    if track:
        artist = track.get_artist()
        track.username = lastUser

        embed.description = track.get_name()
        embed.set_thumbnail(url=track.get_cover_image())
        embed.add_field(name="Artist", value=artist.get_correction()) # not totally correct tho
        # embed.add_field(name="Artist", value=artist.get_name())
        # embed.add_field(name="Artist", value=artist.get_name(properly_capitalized=True))
        # embed.add_field(name="Artist", value=str(artist))
        embed.add_field(name="\u200B", value="\u200B", inline=True)
        embed.add_field(name="Album", value=track.get_album().get_name(), inline=True)
        embed.set_footer(text=f"User playcount: {track.get_userplaycount()}")
    else:
        embed.description = "None"

    # TODO: artist link? duration? check if lastfm account exists

    await ctx.respond(embed=embed)

# Recent tracks
@bot.slash_command(
    guild_ids=GUILD_IDS,
    description="Display recent tracks"
)
async def recenttracks(ctx):
    user = ctx.author
    discID = str(user.id)
    if discID not in fileDict.keys():
        await ctx.respond("User has not set Last.fm account")
        return

    lastUser = network.get_user(fileDict[discID])

    extract = lastUser.get_recent_tracks(limit=20)

    index = 1
    ans = ""

    for item in extract:
        ans = f"{ans}\n{index}. **{item.track}**"
        index+=1
    
    embed = discord.Embed(
        title="Recent Tracks:",
        description=ans,
        color=user.color
    )
    embed.set_author(name=user.display_name, icon_url=user.display_avatar)

    await ctx.respond(embed=embed)

# Top artists
@bot.slash_command(
    guild_ids=GUILD_IDS,
    description="Display most listened artists"
)
async def topartists(
    ctx,
    mention: Option(str, "Enter @user", required=False),
    limit: Option(int, "Enter amount to display", default=10, min_value=1, max_value=100)
):
    if mention:
        id = get_id_from_mention(mention)
        user = await ctx.guild.fetch_member(id)
    else:
        user = ctx.author
    
    discID = str(user.id)
    if discID not in fileDict.keys():
        await ctx.respond("User has not set Last.fm account")
        return

    lastUser = network.get_user(fileDict[discID])

    # extract is list of (artist, plays)
    extract = lastUser.get_top_artists(limit=limit)

    # print(extract)

    index = 1
    ans = ""

    for topItem in extract:
        ans = f"{ans}\n{index}. **{str(topItem[0])}** | {str(topItem[1])} plays"
        index+=1

    embed = discord.Embed(
        title="Top Artists (All Time):",
        description=ans,
        color=user.color
    )
    embed.set_author(name=user.display_name, icon_url=user.display_avatar)
    # i = topItem[0].get_image()
    # TODO: try to get an image
    # embed.set_thumbnail(url=i)

    await ctx.respond(embed=embed)

# Top tracks
@bot.slash_command(
    guild_ids=GUILD_IDS,
    description="Display your most listened tracks"
)
async def toptracks(
    ctx,
    mention: Option(str, "Enter @user", required=False),
    limit: Option(int, "Enter amount to display", default=10, min_value=1, max_value=100)
):
    if mention:
        id = get_id_from_mention(mention)
        user = await ctx.guild.fetch_member(id)
    else:
        user = ctx.author
    
    discID = str(user.id)
    if discID not in fileDict.keys():
        await ctx.respond("User has not set Last.fm account")
        return
    
    lastUser = network.get_user(fileDict[discID])

    # extract is list of (track, plays)
    extract = lastUser.get_top_tracks(limit=limit)

    index = 1
    ans = ""

    for topItem in extract:
        ans = f"{ans}\n{index}. **{str(topItem[0])}** | {str(topItem[1])} plays"
        index+=1
    
    embed = discord.Embed(
        title="Top Tracks (All Time):",
        description=ans,
        color=user.color
    )
    embed.set_author(name=user.display_name, icon_url=user.display_avatar)
    # i = extract[0,0].get_cover_image()
    # embed.set_thumbnail(url=i)
    # dont use image, they dont exist sometimes / nvm pylast doesnt do this right

    await ctx.respond(embed=embed)

# Who knows
@bot.slash_command(
    guild_ids=GUILD_IDS,
    description="Display everyone's plays from artist"
)
async def wk(ctx, artist: Option(str, "Enter artist", default="np")):
    members = []
    async for m in ctx.guild.fetch_members(limit=None):
        members.append(str(m.id))

    if (artist == "np"):
        user = ctx.author
        discID = str(user.id)
        if discID not in fileDict.keys():
            await ctx.respond("User has not set Last.fm account")
            return
    
        lastUser = network.get_user(fileDict[discID])
        track = lastUser.get_now_playing()
        if (not track):
            await ctx.respond("Nothing currently playing")
            return
        fmArtist = track.get_artist()
    else:
        fmArtist = network.get_artist(artist)

    board = {}
    for key in fileDict:
        if (key in members):
            fmArtist.username = fileDict[key]
            board[key] = fmArtist.get_userplaycount()
    
    # print("board = " + str(board))

    # TODO: pages of people

    sortedKeys = sorted(board, key=board.get, reverse=True)
    # print(sortedKeys)
    
    index = 1
    ans = ""

    for k in sortedKeys:
        if (board[k] > 0):
            u = await ctx.guild.fetch_member(k)
            ans = f"{ans}\n{index}. **{u.display_name}** | {str(board[k])} plays"
            index+=1

    embed = discord.Embed(
        title=f"Who knows: {str(fmArtist)}",
        description=ans,
        color=ctx.author.color #not user but try to get artist color
    )
    # get pic of artist; musicbrainz?

    await ctx.respond(embed=embed)

# Test
@bot.slash_command(
    guild_ids=GUILD_IDS,
    description="Test function"
)
async def test(ctx):
    
    await ctx.respond('hi')

bot.run(TOKEN)



# Method 1: Client
# client = discord.Client()

# @client.event
# async def on_ready():
#     print(f'{client.user} has connected to Discord!')

# @client.event
# async def on_message(message):
#     if message.author == client.user:
#         return

#     if message.content == 'ping':
#         response = 'pong'
#         await message.channel.send(response)

# client.run(TOKEN)


# Method 2: Bot
# bot = commands.Bot(command_prefix=';')

# @bot.event
# async def on_ready():
#     print(f'{bot.user} has connected to Discord!')

# @bot.command(name='ping')
# async def ping(ctx):
#     response = 'pong'
#     await ctx.send(response)

# bot.run(TOKEN)


# Method 3: Slash
# slash = SlashCommand(bot, sync_commands=True)

# @slash.slash(
#     name = "hello",
#     description = "Just sends a message",
#     guild_ids = [632049514001203227],
#     options = [
#         create_option(
#             name = "option",
#             description = "Choose your word!",
#             required = True,
#             option_type = 3,
#             choices = [
#                 create_choice(
#                     name = "World!",
#                     value = "world"
#                 ),
#                 create_choice(
#                     name = "You!",
#                     value = "you"
#                 )
#             ]
#         )
#     ]
# )
# async def hello(ctx:SlashContext, option:str):
#     await ctx.send(option)

# @slash.slash(
#     name = "getuser",
#     description = "Get user ID",
#     guild_ids = [632049514001203227],
#     options = [
#         create_option(
#             name = "user",
#             description = "Select a user",
#             required = True,
#             option_type = 6,
#         )
#     ]
# )
# async def getUser(ctx:SlashContext, user:str):
#     await ctx.send(user.id)
# 
# bot.run(TOKEN)


# Method 4: Interactions
# bot = interactions.Client(token = TOKEN)

# @bot.event
# async def on_ready():
#     print('Raiden has connected to Discord!')

# @bot.command(
#     name = "first",
#     description = "First command.",
#     scope = 632049514001203227
# )
# async def first(ctx:interactions.CommandContext):
#     await ctx.send("Hi")

# @bot.command(
#     name = "say",
#     description = "Say something.",
#     scope = 632049514001203227,
#     options = [
#         interactions.Option(
#             name = "text",
#             description = "What you want to say",
#             type = interactions.OptionType.STRING,
#             required = True
#         )
#     ]
# )
# async def say(ctx:interactions.CommandContext, text:str):
#     await ctx.send(f"You said '{text}'!")

# @bot.command(
#     type = interactions.ApplicationCommandType.USER,
#     name = "User Command",
#     scope = 632049514001203227
# )
# async def test(ctx):
#     await ctx.send(f"You have applied a command onto user {ctx.target.user.username}!")


# button = interactions.Button(
#     style = interactions.ButtonStyle.PRIMARY,
#     label = "hello world!",
#     custom_id = "hello"
# )

# @bot.command(
#     name = "button_test",
#     description = "This is the first button",
#     scope = 632049514001203227
# )
# async def button_test(ctx):
#     await ctx.send("testing", components=button)

# @bot.component("hello")
# async def button_response(ctx):
#     await ctx.send("You clicked the Button :O", ephemeral = True)


# modal = interactions.Modal(
#     title = "Modal",
#     custom_id = "mod_app_form",
#     components = [
#         interactions.TextInput(
#             style = interactions.TextStyleType.SHORT,
#             label = "Let's get straight to it: what's 1 + 1?",
#             custom_id = "text_input_response",
#             min_length = 1,
#             max_length = 3,
#         )
#     ]
# )

# @bot.command(
#     name = "modal",
#     description = "am i doing this right",
#     scope = 632049514001203227
# )
# async def modal_command(ctx):
#     await ctx.popup(modal)


# @bot.modal("mod_app_form")
# async def modal_response(ctx, response: str):
#     await ctx.send(f"You wrote: {response}", ephemeral=True)

# bot.start()


# ---- Stopped midway -----------------
# Test
# @bot.slash_command(
#     guild_ids=GUILD_IDS,
#     description="Test function"
# )
# async def test(ctx, arg1: Option(str, "Enter Discord username", choices=["203262300218458112","206231511303716864"])):
#     author = await ctx.guild.fetch_member(int(arg1))
#     discID = str(author.id)
#     lastUser = fileDict[discID]
#     user = network.get_user(lastUser)

#     birth = date.fromtimestamp(int(user.get_registered()))
#     # TODO: consider timezone, DST

#     embed = discord.Embed(
#         title="Last.fm Profile",
#         description=f"[{user.get_name()}]({user.get_url()})",
#         color=author.color
#     )
#     embed.set_author(name=author.display_name, icon_url=author.display_avatar)
#     embed.add_field(name="Account Created  |", value=birth.strftime("%b %d, %Y"))
#     embed.add_field(name="Total Plays", value=user.get_playcount())
#     if user.get_image():
#         embed.set_thumbnail(url=user.get_image())

#     await ctx.respond(embed=embed)
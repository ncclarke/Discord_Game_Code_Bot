import discord
from discord.ext import commands

TOKEN = "Token_Here"

game_code = "NONE"
game_name = "NONE"
player_count = 0

intents = discord.Intents.default()  # Use default intents
intents.message_content = True       # Enable intent to read message content (for message commands)
intents.guilds = True  # To access guild-related events
intents.members = True  # To access member-related events

# Define the bot's command prefix
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

@bot.command()
async def hello(ctx):
    await ctx.send(f'Hello, {ctx.author.mention}!')

@bot.event
async def on_message(message):
    # Check if the bot is mentioned
    if bot.user.mentioned_in(message) and not message.mention_everyone:
        await message.channel.send(f'Hello {message.author.mention}, you mentioned me!')
    
    # Process other commands
    await bot.process_commands(message)

@bot.command()
async def code(ctx):
    await ctx.send(f'Code: {game_code}')

@bot.command()
async def setCode(ctx, code: str):
    global game_code
    game_code = code
    await ctx.send(f'Code: {code}')

@bot.command()
async def gameName(ctx):
    await ctx.send(f'Game Title: {game_name}')

@bot.command()
async def setGameName(ctx, *, title: str):
    global game_name
    game_name = title
    await ctx.send(f'Game Title set to: {title}')

@bot.command()
async def join(ctx):
    global player_count
    player_count = player_count + 1
    await ctx.send(f'{ctx.author.mention} has joined the game, player count: {player_count}.')

@bot.command()
async def endGame(ctx):
    global game_code
    global game_name
    global player_count

    game_code = "NONE"
    game_name = "NONE"
    player_count = 0

    await ctx.send(f'Game ended')

bot.run(TOKEN)
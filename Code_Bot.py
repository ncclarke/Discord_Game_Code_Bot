import discord
from discord.ext import commands
import mysql.connector
from mysql.connector import errorcode

TOKEN = "TOKEN_HERE"

game_code = "NONE"
game_name = "NONE"
player_count = 0

def get_db_connection():
    try:
        connection = mysql.connector.connect(
            user='testUser',
            password='testUserPassword',
            host='localhost',
            database='discord_code_bot_data'
        )
        return connection
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("Something is wrong with your user name or password")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print("Database does not exist")
        else:
            print(err)
        return None
    
def initialize_database():
    connection = get_db_connection()
    cursor = connection.cursor()

    users_table = """
    CREATE TABLE IF NOT EXISTS users (
        user_id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(255) NOT NULL,
        games_played_count INT DEFAULT 0,
        total_games_won_count INT DEFAULT 0,
        total_loss_count INT DEFAULT 0
    );
    """

    games_table = """
    CREATE TABLE IF NOT EXISTS games (
        game_id INT AUTO_INCREMENT PRIMARY KEY,
        game_name VARCHAR(255) NOT NULL,
        total_games_played INT DEFAULT 0
    );
    """

    wins_table = """
    CREATE TABLE IF NOT EXISTS wins (
        win_id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT,
        game_id INT,
        points_scored INT,
        FOREIGN KEY (user_id) REFERENCES users(user_id),
        FOREIGN KEY (game_id) REFERENCES games(game_id)
    );
    """
    loss_table = """
    CREATE TABLE IF NOT EXISTS losses (
        loss_id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT,
        game_id INT,
        losses_count INT DEFAULT 0,
        FOREIGN KEY (user_id) REFERENCES users(user_id),
        FOREIGN KEY (game_id) REFERENCES games(game_id)
    );
    """


    try:
        cursor.execute(users_table)
        cursor.execute(games_table)
        cursor.execute(wins_table)
        cursor.execute(loss_table)
        connection.commit()
    except mysql.connector.Error as err:
        print(f"Error: {err}")
    finally:
        cursor.close()
        connection.close()

def add_user(user_id, username):
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("""
        INSERT INTO users (user_id, username)
        VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE username = VALUES(username)
    """, (user_id, username))
    connection.commit()
    cursor.close()
    connection.close()

def add_game(game_name):
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("""
        INSERT INTO games (game_name)
        VALUES (%s)
        ON DUPLICATE KEY UPDATE game_name = VALUES(game_name)
    """, (game_name,))
    connection.commit()
    game_id = cursor.lastrowid
    cursor.close()
    connection.close()
    return game_id

def add_win(user_id, game_id, points_scored):
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("""
        INSERT INTO wins (user_id, game_id, points_scored)
        VALUES (%s, %s, %s)
    """, (user_id, game_id, points_scored))
    
    cursor.execute("""
        UPDATE users
        SET games_played_count = games_played_count + 1
        WHERE user_id = %s
    """, (user_id,))

    cursor.execute("""
        UPDATE games
        SET total_games_played = total_games_played + 1
        WHERE game_id = %s
    """, (game_id,))

    connection.commit()
    cursor.close()
    connection.close()

def get_or_create_user(username):
    connection = get_db_connection()
    cursor = connection.cursor()
    
    cursor.execute("SELECT user_id, games_played_count, total_games_won_count, total_loss_count FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()
    
    if user is None:
        cursor.execute("INSERT INTO users (username) VALUES (%s)", (username,))
        connection.commit()
        user_id = cursor.lastrowid
        user = (user_id, 0, 0)  # new user has 0 games played and 0 games won
    else:
        user_id = user[0]

    cursor.close()
    connection.close()

    return user

def get_or_create_game(game_name):
    connection = get_db_connection()
    cursor = connection.cursor()
    
    cursor.execute("SELECT game_id, total_games_played FROM games WHERE game_name = %s", (game_name,))
    game = cursor.fetchone()
    
    if game is None:
        cursor.execute("INSERT INTO games (game_name) VALUES (%s)", (game_name,))
        connection.commit()
        game_id = cursor.lastrowid
        game = (game_id, 0)  # new game has 0 games played
    else:
        game_id = game[0]

    cursor.close()
    connection.close()
    return game

def record_win(username, game_name, score):
    user = get_or_create_user(username)
    user_id, games_played_count, total_games_won_count, total_loss_count = user

    game = get_or_create_game(game_name)
    game_id, total_games_played = game

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO wins (user_id, game_id, points_scored) 
        VALUES (%s, %s, %s)
    """, (user_id, game_id, score))

    cursor.execute("""
        UPDATE users 
        SET games_played_count = games_played_count + 1, 
            total_games_won_count = total_games_won_count + 1 
        WHERE user_id = %s
    """, (user_id,))

    cursor.execute("""
        UPDATE games 
        SET total_games_played = total_games_played + 1 
        WHERE game_id = %s
    """, (game_id,))

    connection.commit()
    cursor.close()
    connection.close()

def get_or_create_loss(username, game_name):
    connection = get_db_connection()
    cursor = connection.cursor()
    
    cursor.execute("SELECT game_id, total_games_played FROM games WHERE game_name = %s", (game_name,))
    game = cursor.fetchone()
    
    if game is None:
        cursor.execute("INSERT INTO games (game_name) VALUES (%s)", (game_name,))
        connection.commit()
        game_id = cursor.lastrowid
        game = (game_id, 0)  # new game has 0 games played
    else:
        game_id = game[0]

    cursor.close()
    connection.close()
    return game

def record_loss(username, game_name):
    user = get_or_create_user(username)
    user_id, games_played_count, total_games_won_count, total_loss_count = user

    game = get_or_create_game(game_name)
    game_id = game[0]

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO losses (user_id, game_id, losses_count) 
        VALUES (%s, %s, 1) 
        ON DUPLICATE KEY UPDATE losses_count = losses_count + 1
    """, (user_id, game_id))

    cursor.execute("""
        UPDATE users 
        SET total_loss_count = total_loss_count + 1 
        WHERE user_id = %s
    """, (user_id,))

    connection.commit()

     # Fetch the updated losses_count for the current user and game
    cursor.execute("""
        SELECT losses_count 
        FROM losses 
        WHERE user_id = %s AND game_id = %s
    """, (user_id, game_id))

    losses_count = cursor.fetchone()[0]

    cursor.close()
    connection.close()

    return losses_count



intents = discord.Intents.default()  # Use default intents
intents.message_content = True       # Enable intent to read message content (for message commands)
intents.guilds = True  # To access guild-related events
intents.members = True  # To access member-related events

# Define the bot's command prefix
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    initialize_database()  # Initialize the database and create tables if necessary
    print('Database initialized and tables created if they did not exist.')

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

@bot.command()
async def win(ctx, score: int):
    global game_name
    username = str(ctx.author)
    
    if game_name == "NONE":
        await ctx.send("No game has been set. Use !setGameName <title> to set the game name.")
        return
    
    record_win(username, game_name, score)
    await ctx.send(f"{ctx.author.mention} has won '{game_name}' with a score of {score}!")

@bot.command()
async def lose(ctx):
    global game_name
    username = str(ctx.author)
    
    if game_name == "NONE":
        await ctx.send("No game has been set. Use !setGameName <title> to set the game name.")
        return
    losses = record_loss(username, game_name)
    await ctx.send(f"{ctx.author.mention} has lost '{game_name}' they have a total of {losses} for this game.")

@bot.command()
async def test_win(ctx):
    global game_name
    username = str(ctx.author)
    
    if game_name == "NONE":
        await ctx.send("No game has been set. Use !setGameName <title> to set the game name.")
        return
    
    #record_win(username, game_name, score)
    await ctx.send(f"{ctx.author.mention} has won '{game_name}' with a score of test!")

bot.run(TOKEN)
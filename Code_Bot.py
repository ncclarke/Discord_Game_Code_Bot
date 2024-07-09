import discord
from discord.ext import commands
import mysql.connector
from mysql.connector import errorcode

TOKEN = "TOKEN_HERE"

game_code = "NONE"
game_name = "NONE"
player_count = 0

#get MYSQL connection
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

#set up tables in MYSQL  
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

#retrives user, or creates a new object in the database for the user if it does not exist
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

#retrieves game, or creates new object in the database for the game if it does not exist
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

#used to track a win
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

    connection.commit()
    cursor.close()
    connection.close()

#used to track a loss
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
        SET total_loss_count = total_loss_count + 1, 
        games_played_count = games_played_count + 1
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

#gets total wins for a user
def get_win_total(username):
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT total_games_won_count 
        FROM users 
        WHERE username = %s
    """, (username,))
    
    result = cursor.fetchone()
    win_total = result[0] if result else 0

    cursor.close()
    connection.close()

    return win_total

#gets loss total for user
def get_loss_total(username):
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT total_loss_count 
        FROM users 
        WHERE username = %s
    """, (username,))
    
    result = cursor.fetchone()
    loss_total = result[0] if result else 0

    cursor.close()
    connection.close()

    return loss_total

#gets total games played by a user
def get_played_games_total(username):
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT games_played_count 
        FROM users 
        WHERE username = %s
    """, (username,))
    
    result = cursor.fetchone()
    total = result[0] if result else 0

    cursor.close()
    connection.close()

    return total

#gets overall stats for a user (games won, lost, and played and max score) for a particular game
def get_player_stats(username, game_name):
    user = get_or_create_user(username)
    user_id = user[0]

    game = get_or_create_game(game_name)
    game_id = game[0]


    connection = get_db_connection()
    cursor = connection.cursor()

     # Total times won
    cursor.execute("SELECT COUNT(*) FROM wins WHERE user_id = %s AND game_id = %s", (user_id, game_id))
    total_times_won = cursor.fetchone()[0]

    # Total times lost
    cursor.execute("SELECT losses_count FROM losses WHERE user_id = %s AND game_id = %s", (user_id, game_id))
    result = cursor.fetchone()
    total_times_lost = result[0] if result else 0

    total_times_played = total_times_won + total_times_lost

    # Highest score
    cursor.execute("SELECT MAX(points_scored) FROM wins WHERE user_id = %s AND game_id = %s", (user_id, game_id))
    highest_score = cursor.fetchone()[0] or 0

    cursor.close()
    connection.close()

    return {
        "username": username,
        "game_name": game_name,
        "total_times_played": total_times_played,
        "total_times_won": total_times_won,
        "total_times_lost": total_times_lost,
        "highest_score": highest_score
    }

#gets user will most wins for a particular game
def get_top_winner(game_name):
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT u.username, COUNT(w.win_id) AS win_count
        FROM users u
        JOIN wins w ON u.user_id = w.user_id
        JOIN games g ON w.game_id = g.game_id
        WHERE g.game_name = %s
        GROUP BY u.username
        ORDER BY win_count DESC
        LIMIT 1;
    """, (game_name,))
    
    result = cursor.fetchone()
    cursor.close()
    connection.close()

    if result:
        return {"username": result[0], "win_count": result[1]}
    else:
        return None

#gets user with record points for a particular game
def get_points_record_holder(game_name):
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT u.username, MAX(w.points_scored) AS highest_points
        FROM users u
        JOIN wins w ON u.user_id = w.user_id
        JOIN games g ON w.game_id = g.game_id
        WHERE g.game_name = %s
        GROUP BY u.username
        ORDER BY highest_points DESC
        LIMIT 1;
    """, (game_name,))
    
    result = cursor.fetchone()
    cursor.close()
    connection.close()

    if result:
        return {"username": result[0], "highest_points": result[1]}
    else:
        return None
    



intents = discord.Intents.default()  # Use default intents
intents.message_content = True       # Enable intent to read message content (for message commands)
intents.guilds = True  # To access guild-related events
intents.members = True  # To access member-related events

# Define the bot's command prefix
bot = commands.Bot(command_prefix='!', intents=intents)

#initalizes database upon starting bots
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    initialize_database()  # Initialize the database and create tables if necessary
    print('Database initialized and tables created if they did not exist.')

#testing command
# @bot.command()
# async def hello(ctx):
#     await ctx.send(f'Hello, {ctx.author.mention}!')

#testing mentioning bot
@bot.event
async def on_message(message):
    # Check if the bot is mentioned
    if bot.user.mentioned_in(message) and not message.mention_everyone:
        await message.channel.send(f'Hello {message.author.mention}, you mentioned me!')
    
    # Process other commands
    await bot.process_commands(message)

#returns game code
@bot.command()
async def code(ctx):
    await ctx.send(f'Code: {game_code}')

#sets game code
@bot.command()
async def setCode(ctx, code: str):
    global game_code
    game_code = code
    await ctx.send(f'Code: {code}')

#returns game name
@bot.command()
async def gameName(ctx):
    await ctx.send(f'Game Title: {game_name}')

#sets game name
@bot.command()
async def setGameName(ctx, *, title: str):
    global game_name
    game_name = title
    await ctx.send(f'Game Title set to: {title}')

#increases player count
@bot.command()
async def join(ctx):
    global player_count
    player_count = player_count + 1
    await ctx.send(f'{ctx.author.mention} has joined the game, player count: {player_count}.')

#ends game and increases play count
@bot.command()
async def endGame(ctx):
    global game_code
    global game_name
    global player_count

    #If there is an active game, update the total_games_played count
    if game_name != "NONE":
        connection = get_db_connection()
        cursor = connection.cursor()
        
        # Fetch the game_id using the current game_name
        cursor.execute("SELECT game_id FROM games WHERE game_name = %s", (game_name,))
        result = cursor.fetchone()
        
        if result:
            game_id = result[0]
            # Increment the total_games_played count for the game
            cursor.execute("UPDATE games SET total_games_played = total_games_played + 1 WHERE game_id = %s", (game_id,))
            connection.commit()
        
        cursor.close()
        connection.close()

    game_code = "NONE"
    game_name = "NONE"
    player_count = 0

    await ctx.send(f'Game ended')

#tracks a game win
@bot.command()
async def win(ctx, score: int):
    global game_name
    username = str(ctx.author)
    
    if game_name == "NONE":
        await ctx.send("No game has been set. Use !setGameName <title> to set the game name.")
        return
    
    record_win(username, game_name, score)
    await ctx.send(f"{ctx.author.mention} has won '{game_name}' with a score of {score}!")

#tracks a game loss
@bot.command()
async def lose(ctx):
    global game_name
    username = str(ctx.author)
    
    if game_name == "NONE":
        await ctx.send("No game has been set. Use !setGameName <title> to set the game name.")
        return
    losses = record_loss(username, game_name)
    await ctx.send(f"{ctx.author.mention} has lost '{game_name}' they have a total of {losses} losses for this game.")

#returns total wins
@bot.command()
async def totalWins(ctx):
    username = str(ctx.author)
    win_total = get_win_total(username)
    await ctx.send(f"{ctx.author.mention}, has {win_total} total wins.")

#returns total losses
@bot.command()
async def totalLosses(ctx):
    username = str(ctx.author)
    loss_total = get_loss_total(username)
    await ctx.send(f"{ctx.author.mention}, has {loss_total} total losses.")

#returns total plays
@bot.command()
async def totalPlayed(ctx):
    username = str(ctx.author)
    total = get_played_games_total(username)
    await ctx.send(f"{ctx.author.mention}, has played a total of {total} games.")

#return overall stats for a user (wins, losses, games played)
@bot.command()
async def overallStats(ctx):
    username = str(ctx.author)
    win_total = get_win_total(username)
    loss_total = get_loss_total(username)
    games_total = get_played_games_total(username)
    await ctx.send(f"{ctx.author.mention}, has played a total of {games_total} games. They have won {win_total} games, and lost {loss_total} games.")

#returns stats for a particular game for a user
@bot.command()
async def stats(ctx, *, game_name: str):
    username = str(ctx.author)
    stats = get_player_stats(username, game_name)
    if isinstance(stats, str):
        await ctx.send(stats)
    else:
        await ctx.send(f"Stats for {ctx.author.mention} for game '{game_name}':\n"
                       f"Total Times Played: {stats['total_times_played']}\n"
                       f"Total Wins: {stats['total_times_won']}\n"
                       f"Total Losses: {stats['total_times_lost']}\n"
                       f"High Score: {stats['highest_score']}")

#returns the win leader for a particular game
@bot.command()
async def winLeader(ctx, *, game_name: str):
    top_winner = get_top_winner(game_name)

    if top_winner:
        response = f"The top winner for '{game_name}' is {top_winner['username']} with {top_winner['win_count']} wins."
    else:
        response = f"No wins recorded for the game '{game_name}'."

    await ctx.send(response)

#returns highest score for a particular game
@bot.command()
async def pointsLeader(ctx, *, game_name: str):
    record_holder = get_points_record_holder(game_name)

    if record_holder:
        response = f"The points record holder for '{game_name}' is {record_holder['username']} with {record_holder['highest_points']} points."
    else:
        response = f"No points record found for the game '{game_name}'."

    await ctx.send(response)

#returns total times played for a particular game
@bot.command()
async def totalPlays(ctx, *, game_name: str):
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT total_games_played FROM games WHERE game_name = %s", (game_name,))
    result = cursor.fetchone()

    if result:
        total_games_played = result[0]
        await ctx.send(f'Total times {game_name} has been played: {total_games_played}')
    else:
        await ctx.send(f'Game "{game_name}" not found.')

    cursor.close()
    connection.close()

#returns number of times played for all games and a total
@bot.command()
async def timesPlayedAll(ctx):
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT game_name, total_games_played FROM games")
    results = cursor.fetchall()

    if results:
        overallTotal = 0
        response = "Total number of times each game was played: \n"

        for row in results:
            game_name, total_games_played = row
            overallTotal += total_games_played
            response += f'{game_name}: {total_games_played}\n'

        response += f'Overall total games played: {overallTotal}'
        await ctx.send(response)
    else:
        await ctx.send("No games found in the database.")
        
bot.run(TOKEN)
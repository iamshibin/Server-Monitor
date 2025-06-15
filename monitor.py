import os
import json
import asyncio
from datetime import datetime, timedelta
import discord
from discord.ext import commands, tasks
import git
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_ID = int(os.getenv('GUILD_ID'))
INTERVAL = int(os.getenv('INTERVAL'))
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
GITHUB_USERNAME = os.getenv('GITHUB_USERNAME')
GITHUB_REPO = os.getenv('GITHUB_REPO')
GITHUB_EMAIL = os.getenv('GITHUB_EMAIL')

# File paths
DATA_DIR = 'data'
MESSAGES_FILE = os.path.join(DATA_DIR, 'messages.json')
MEMBER_COUNT_FILE = os.path.join(DATA_DIR, 'member_count.json')

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

# Initialize bot
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

def load_json(file_path):
    """Load JSON data from file or return empty list if file doesn't exist."""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_json(file_path, data):
    """Save data to JSON file."""
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)

def commit_to_github():
    """Commit changes to GitHub repository."""
    try:
        repo = git.Repo('.')
        repo.git.add(update=True)
        repo.index.commit(f'Update server stats {datetime.now().isoformat()}')
        origin = repo.remote(name='origin')
        origin.push()
        print("Changes committed and pushed to GitHub")
    except Exception as e:
        print(f"Error committing to GitHub: {e}")

async def update_stats():
    """Update server statistics."""
    guild = bot.get_guild(GUILD_ID)
    if not guild:
        print("Guild not found")
        return

    # Get message count (approximate for last 10 minutes)
    messages_last_10min = 0
    try:
        # Get messages from all channels in the last 10 minutes
        ten_min_ago = datetime.utcnow() - timedelta(minutes=10)
        for channel in guild.text_channels:
            try:
                messages = [msg async for msg in channel.history(limit=None, after=ten_min_ago)]
                messages_last_10min += len(messages)
            except discord.Forbidden:
                continue  # Skip channels we don't have permission to read
    except Exception as e:
        print(f"Error counting messages: {e}")

    # Get member counts
    total_members = guild.member_count
    online_members = sum(1 for member in guild.members if member.status != discord.Status.offline)

    # Current timestamp
    timestamp = datetime.utcnow().isoformat()

    # Update messages.json
    messages_data = load_json(MESSAGES_FILE)
    messages_data.append({
        "timestamp": timestamp,
        "messages_last_10min": messages_last_10min
    })
    save_json(MESSAGES_FILE, messages_data)

    # Update member_count.json
    member_count_data = load_json(MEMBER_COUNT_FILE)
    member_count_data.append({
        "timestamp": timestamp,
        "total_members": total_members,
        "online_members": online_members
    })
    save_json(MEMBER_COUNT_FILE, member_count_data)

    # Commit changes to GitHub
    commit_to_github()

@tasks.loop(minutes=INTERVAL)
async def monitor_loop():
    """Main monitoring loop that runs every INTERVAL minutes."""
    await update_stats()

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} ({bot.user.id})')
    print('------')
    monitor_loop.start()

# Run the bot
if __name__ == '__main__':
    bot.run(DISCORD_TOKEN)
import os
import json
import asyncio
import logging
from datetime import datetime, timedelta
import discord
from discord.ext import commands, tasks
import git
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bot.log')
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configuration
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
if not DISCORD_TOKEN:
    logger.error("DISCORD_TOKEN not found in .env file")
    exit(1)

GUILD_ID = os.getenv('GUILD_ID')
if not GUILD_ID:
    logger.error("GUILD_ID not found in .env file")
    exit(1)
try:
    GUILD_ID = int(GUILD_ID)
except ValueError:
    logger.error(f"Invalid GUILD_ID: {GUILD_ID}. Must be an integer.")
    exit(1)

INTERVAL = os.getenv('INTERVAL', '10')
try:
    INTERVAL = int(INTERVAL)
except ValueError:
    logger.error(f"Invalid INTERVAL: {INTERVAL}. Must be an integer.")
    exit(1)

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
logger.info(f"Data directory ready at: {os.path.abspath(DATA_DIR)}")

# Initialize bot
intents = discord.Intents.default()
intents.members = True  # Needed for member count tracking
intents.message_content = True  # Needed for message tracking
bot = commands.Bot(command_prefix='!', intents=intents)


def load_json(file_path):
    """Load JSON data from file or return empty list if file doesn't exist."""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(f"File not found, creating new: {file_path}")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from {file_path}: {e}")
        return []


def save_json(file_path, data):
    """Save data to JSON file."""
    try:
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
        logger.info(f"Successfully saved data to {file_path}")
    except Exception as e:
        logger.error(f"Error saving to {file_path}: {e}")


def commit_to_github():
    """Commit changes to GitHub repository."""
    try:
        # Configure git user
        repo = git.Repo('.')
        with repo.config_writer() as git_config:
            if GITHUB_USERNAME:
                git_config.set_value('user', 'name', GITHUB_USERNAME)
            if GITHUB_EMAIL:
                git_config.set_value('user', 'email', GITHUB_EMAIL)

        # Check if there are changes to commit
        changed_files = [item.a_path for item in repo.index.diff(None)] + repo.untracked_files
        if not changed_files:
            logger.info("No changes detected, skipping commit")
            return

        logger.info(f"Preparing to commit {len(changed_files)} files: {changed_files}")

        # Add all changes
        repo.git.add(update=True)
        commit_message = f'Update server stats {datetime.now().isoformat()}'
        repo.index.commit(commit_message)
        logger.info(f"Committed changes with message: '{commit_message}'")

        # Push changes
        if GITHUB_TOKEN:
            origin = repo.remote(name='origin')
            with origin.config_writer as config:
                url = origin.url
                if url.startswith('https://'):
                    authenticated_url = f"https://{GITHUB_TOKEN}@github.com/{GITHUB_USERNAME}/{GITHUB_REPO}.git"
                    config.set('url', authenticated_url)

            push_info = origin.push()
            for info in push_info:
                logger.info(f"Push result: {info.summary}")
            logger.info("Successfully pushed changes to GitHub")
        else:
            logger.warning("GITHUB_TOKEN not found, changes committed locally but not pushed")

    except git.exc.InvalidGitRepositoryError:
        logger.error("Not a valid Git repository. Please run this in a cloned GitHub repository.")
    except Exception as e:
        logger.error(f"Error committing to GitHub: {str(e)}", exc_info=True)


async def update_stats():
    """Update server statistics."""
    try:
        guild = bot.get_guild(GUILD_ID)
        if not guild:
            logger.error(f"Guild with ID {GUILD_ID} not found")
            return

        logger.info(f"Updating stats for guild: {guild.name} (ID: {guild.id})")

        # Get message count (approximate for last 10 minutes)
        messages_last_10min = 0
        ten_min_ago = datetime.utcnow() - timedelta(minutes=10)
        logger.info(f"Counting messages since {ten_min_ago.isoformat()}")

        for channel in guild.text_channels:
            try:
                logger.debug(f"Checking channel: {channel.name}")
                messages = [msg async for msg in channel.history(limit=None, after=ten_min_ago)]
                messages_last_10min += len(messages)
                logger.debug(f"Found {len(messages)} messages in {channel.name}")
            except discord.Forbidden:
                logger.warning(f"No permission to read channel: {channel.name}")
                continue
            except Exception as e:
                logger.error(f"Error counting messages in {channel.name}: {e}", exc_info=True)
                continue

        logger.info(f"Total messages in last 10 minutes: {messages_last_10min}")

        # Get member counts
        total_members = guild.member_count
        online_members = sum(1 for member in guild.members if member.status != discord.Status.offline)
        logger.info(f"Member stats - Total: {total_members}, Online: {online_members}")

        # Current timestamp
        timestamp = datetime.utcnow().isoformat()
        logger.info(f"Recording stats at timestamp: {timestamp}")

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

    except Exception as e:
        logger.error(f"Error in update_stats: {e}", exc_info=True)


@tasks.loop(minutes=INTERVAL)
async def monitor_loop():
    """Main monitoring loop that runs every INTERVAL minutes."""
    logger.info("Starting monitoring cycle")
    await update_stats()
    logger.info("Monitoring cycle completed")


@monitor_loop.before_loop
async def before_monitor():
    """Wait until bot is ready before starting monitoring."""
    await bot.wait_until_ready()
    logger.info("Bot is ready, starting monitoring loop")


@bot.event
async def on_ready():
    logger.info(f'Logged in as {bot.user.name} (ID: {bot.user.id})')
    logger.info(f'Connected to {len(bot.guilds)} guild(s)')
    for guild in bot.guilds:
        logger.info(f' - {guild.name} (ID: {guild.id})')
    logger.info('------')
    monitor_loop.start()  # Start the monitoring loop when bot is ready


@bot.event
async def on_error(event, *args, **kwargs):
    logger.error(f'Error in event {event}:', exc_info=True)


# Run the bot
if __name__ == '__main__':
    logger.info("Starting bot...")
    try:
        bot.run(DISCORD_TOKEN)
    except discord.LoginFailure:
        logger.error("Invalid Discord token. Please check your DISCORD_TOKEN in .env")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
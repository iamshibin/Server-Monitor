import discord
from discord.ext import commands, tasks
import json
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
import logging
import subprocess

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_ID = int(os.getenv('GUILD_ID'))
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
GITHUB_USERNAME = os.getenv('GITHUB_USERNAME')
GITHUB_REPO = os.getenv('GITHUB_REPO')
GITHUB_EMAIL = os.getenv('GITHUB_EMAIL')

# Initialize bot
intents = discord.Intents.default()
intents.members = True
intents.presences = True
bot = commands.Bot(command_prefix='!', intents=intents)


class DataManager:
    def __init__(self):
        self.data_dir = 'data'
        self.member_file = os.path.join(self.data_dir, 'member_count.json')
        self.message_file = os.path.join(self.data_dir, 'messages.json')
        self.setup_data_files()

    def setup_data_files(self):
        """Ensure data directory and files exist"""
        os.makedirs(self.data_dir, exist_ok=True)
        for file in [self.member_file, self.message_file]:
            if not os.path.exists(file):
                with open(file, 'w') as f:
                    json.dump([], f)

    def load_data(self, file_path):
        """Load JSON data from file"""
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def save_data(self, file_path, data):
        """Save data to JSON file"""
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)


class GitManager:
    def __init__(self):
        self.repo_path = os.getcwd()
        self.git_configured = False
        self.initialize_repository()

    def run_git_command(self, command, check=True):
        """Run a git command and return the result"""
        try:
            result = subprocess.run(
                ['git'] + command,
                cwd=self.repo_path,
                check=check,
                capture_output=True,
                text=True
            )
            return result
        except subprocess.CalledProcessError as e:
            logger.error(f"Git command failed: {' '.join(command)}\nError: {e.stderr}")
            return None

    def initialize_repository(self):
        """Initialize and configure git repository"""
        # Check if we have minimal configuration
        if not all([GITHUB_USERNAME, GITHUB_EMAIL]):
            logger.warning("GitHub username or email not configured - Git functions will be limited")
            return

        # Initialize repository if it doesn't exist
        if not os.path.exists(os.path.join(self.repo_path, '.git')):
            init_result = self.run_git_command(['init'])
            if not init_result:
                logger.error("Failed to initialize git repository")
                return

            # Configure git user (local config)
            self.run_git_command(['config', 'user.name', GITHUB_USERNAME])
            self.run_git_command(['config', 'user.email', GITHUB_EMAIL])

            # Add remote if credentials are available
            if all([GITHUB_TOKEN, GITHUB_USERNAME, GITHUB_REPO]):
                remote_url = f"https://{GITHUB_USERNAME}:{GITHUB_TOKEN}@github.com/{GITHUB_USERNAME}/{GITHUB_REPO}.git"
                self.run_git_command(['remote', 'add', 'origin', remote_url])

                # First pull with --allow-unrelated-histories if needed
                pull_result = self.run_git_command(['pull', 'origin', 'main', '--allow-unrelated-histories'])
                if not pull_result:
                    logger.warning("Initial pull from remote failed - continuing with local repository")

            # Create initial commit
            self.run_git_command(['add', '.'])
            commit_result = self.run_git_command(['commit', '-m', 'Initial commit'])
            if not commit_result:
                logger.error("Initial commit failed - trying with forced author")
                # Try again with explicit author
                commit_result = self.run_git_command([
                    '-c', f'user.name={GITHUB_USERNAME}',
                    '-c', f'user.email={GITHUB_EMAIL}',
                    'commit', '-m', 'Initial commit'
                ])
                if not commit_result:
                    logger.error("Still failed to create initial commit")
                    return

            self.run_git_command(['branch', '-M', 'main'])
        else:
            # Repository exists, just configure user
            self.run_git_command(['config', 'user.name', GITHUB_USERNAME])
            self.run_git_command(['config', 'user.email', GITHUB_EMAIL])

        # Verify git is properly configured
        name_check = self.run_git_command(['config', 'user.name'])
        email_check = self.run_git_command(['config', 'user.email'])

        if name_check and email_check and name_check.stdout.strip() == GITHUB_USERNAME and email_check.stdout.strip() == GITHUB_EMAIL:
            self.git_configured = True
            logger.info("Git repository successfully configured")
        else:
            logger.error("Failed to configure git repository")

    def commit_and_push(self):
        """Commit changes and push to remote"""
        if not self.git_configured:
            logger.warning("Git not properly configured - skipping commit/push")
            return False

        # Add all changes
        self.run_git_command(['add', '.'])

        # Check if there are changes to commit
        status = self.run_git_command(['status', '--porcelain'])
        if not status or not status.stdout.strip():
            logger.info("No changes to commit")
            return False

        # Commit changes
        commit_message = f"Update stats - {datetime.utcnow().isoformat()}"
        commit_result = self.run_git_command(['commit', '-m', commit_message])
        if not commit_result:
            # Try again with explicit author
            commit_result = self.run_git_command([
                '-c', f'user.name={GITHUB_USERNAME}',
                '-c', f'user.email={GITHUB_EMAIL}',
                'commit', '-m', commit_message
            ])
            if not commit_result:
                return False

        # Push to remote if configured
        if all([GITHUB_TOKEN, GITHUB_USERNAME, GITHUB_REPO]):
            # First pull any changes to avoid conflicts
            pull_result = self.run_git_command(['pull', 'origin', 'main', '--rebase'])
            if not pull_result:
                logger.warning("Pull before push failed - attempting push anyway")

            push_result = self.run_git_command(['push', 'origin', 'main'])
            if not push_result:
                # Try force push if normal push fails (only for this initial setup)
                push_result = self.run_git_command(['push', 'origin', 'main', '--force'])
                return push_result is not None

        return True


class StatsBot:
    def __init__(self):
        self.data = DataManager()
        self.git = GitManager()

    async def update_member_stats(self, guild):
        """Update member count statistics"""
        timestamp = datetime.utcnow().isoformat()
        online_members = sum(1 for member in guild.members if member.status != discord.Status.offline)

        new_entry = {
            'timestamp': timestamp,
            'total_members': guild.member_count,
            'online_members': online_members
        }

        member_data = self.data.load_data(self.data.member_file)
        member_data.append(new_entry)
        self.data.save_data(self.data.member_file, member_data)
        logger.info(f"Updated member stats: {guild.member_count} total, {online_members} online")

    async def update_message_stats(self, guild):
        """Update message count statistics"""
        timestamp = datetime.utcnow().isoformat()
        ten_minutes_ago = datetime.utcnow() - timedelta(minutes=10)
        total_messages = 0

        for channel in guild.text_channels:
            try:
                if channel.permissions_for(guild.me).read_message_history:
                    async for _ in channel.history(after=ten_minutes_ago, limit=None):
                        total_messages += 1
            except discord.Forbidden:
                logger.warning(f"No permission to read history in {channel.name}")

        new_entry = {
            'timestamp': timestamp,
            'messages_last_10min': total_messages
        }

        message_data = self.data.load_data(self.data.message_file)
        message_data.append(new_entry)
        self.data.save_data(self.data.message_file, message_data)
        logger.info(f"Updated message stats: {total_messages} messages in last 10 minutes")

    async def collect_stats(self, guild):
        """Collect all statistics"""
        await self.update_member_stats(guild)
        await self.update_message_stats(guild)
        if self.git.commit_and_push():
            logger.info("Successfully committed and pushed changes to GitHub")
        else:
            logger.warning("No changes to commit or push failed")


# Initialize the bot
stats_bot = StatsBot()


@bot.event
async def on_ready():
    """When the bot is ready"""
    logger.info(f'{bot.user} has connected to Discord!')

    guild = bot.get_guild(GUILD_ID)
    if guild:
        await stats_bot.collect_stats(guild)
        collect_stats.start()
    else:
        logger.error(f"Could not find guild with ID {GUILD_ID}")


@tasks.loop(minutes=10)
async def collect_stats():
    """Collect statistics every 10 minutes"""
    guild = bot.get_guild(GUILD_ID)
    if guild:
        await stats_bot.collect_stats(guild)


@collect_stats.before_loop
async def before_collect_stats():
    """Wait for bot to be ready before starting"""
    await bot.wait_until_ready()


if __name__ == '__main__':
    if not TOKEN:
        logger.error("DISCORD_TOKEN not found in environment variables")
        exit(1)

    if not GUILD_ID:
        logger.error("GUILD_ID not found in environment variables")
        exit(1)

    bot.run(TOKEN)

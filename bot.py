# ==========================================================
# bot.py
# Descrizione: Entry point principale del bot Discord. Gestisce l'avvio, la configurazione, il caricamento dei cog, la gestione dei segnali di chiusura e il logging avanzato delle attività utente.
# Dipendenze principali: discord, discord.ext.commands, utils.wordpress_handler, utils.youtube_handler, config/config.json, config/messages.json, logging, asyncio, signal, os, dotenv.
# Flusso di lavoro: Avvia il bot, carica i cog dalla cartella cogs/, gestisce i comandi e gli eventi globali, si occupa della chiusura sicura e del logging delle attività. Tutti i comandi e le funzionalità passano da qui.
# ==========================================================
# Main file for the Discord bot

import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import asyncio
import logging
import signal
import sys
import atexit
import fcntl  # For file locking
import json  # For loading configuration
from utils.wordpress_handler import WordPressHandler
from utils.youtube_handler import YouTubeHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Configure user activity logger
user_logger = logging.getLogger('user_activity')
user_logger.setLevel(logging.INFO)

# Ensure logs directory exists
os.makedirs('logs', exist_ok=True)

# Create file handler for user activity
user_handler = logging.FileHandler('logs/user_activity.log')
user_handler.setFormatter(logging.Formatter(
    '%(asctime)s - User: %(user)s (ID: %(user_id)s) - Channel: %(channel)s (ID: %(channel_id)s) - Guild: %(guild)s (ID: %(guild_id)s) - Message ID: %(message_id)s\n'
    'Content: %(message)s\n'
    'Created: %(created_at)s - Edited: %(edited_at)s\n'
    'Type: %(type)s - System: %(is_system)s - Pinned: %(is_pinned)s\n'
    'Thread: %(thread_info)s\n'
    'Mentions: %(mentions)s\n'
    'Embeds: %(embeds)s - Reactions: %(reactions)s\n'
    'Flags: %(flags)s\n'
    '----------------------------------------',
    '%Y-%m-%d %H:%M:%S'
))
user_logger.addHandler(user_handler)

# Lock file path
LOCK_FILE = "bot.lock"

def check_running():
    """Check if another instance is running using a lock file with file locking"""
    try:
        # Open the lock file in write mode
        lock_file = open(LOCK_FILE, 'w')
        
        try:
            # Try to acquire an exclusive lock
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            
            # If we got here, no other instance is running
            # Write our PID to the file
            lock_file.seek(0)
            lock_file.write(str(os.getpid()))
            lock_file.truncate()
            lock_file.flush()
            
            # Keep the file handle open and store it
            setattr(check_running, '_lock_file', lock_file)
            setattr(check_running, '_cleanup_done', False)
            
            # Register cleanup on exit
            atexit.register(cleanup_lock)
            
        except (IOError, OSError):
            # Another instance has the lock
            logger.error("Another instance of the bot is already running")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Error managing lock file: {e}")
        sys.exit(1)

def cleanup_lock():
    """Remove the lock file and release the lock on exit"""
    # Check if cleanup was already done
    if getattr(check_running, '_cleanup_done', False):
        return
        
    try:
        # Get the stored file handle
        lock_file = getattr(check_running, '_lock_file', None)
        if lock_file:
            # Release the lock and close the file
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            lock_file.close()
        
        # Remove the lock file
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
            logger.info("Lock file removed")
            
        # Mark cleanup as done
        setattr(check_running, '_cleanup_done', True)
            
    except Exception as e:
        if "closed file" not in str(e):  # Don't log closed file errors
            logger.error(f"Error cleaning up lock file: {e}")

# Load environment variables
load_dotenv()

# Bot configuration
TOKEN = os.getenv('DISCORD_TOKEN')
PREFIX = os.getenv('DISCORD_PREFIX')

class Bot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_shutting_down = False
        
        # Load config
        with open('config/config.json', 'r') as f:
            self.config = json.load(f)

    async def close(self):
        if self.is_shutting_down:
            return
        self.is_shutting_down = True
        logger.info("Chiusura del bot in corso...")
        await super().close()
        logger.info("Bot disconnesso correttamente")

    async def on_ready(self):
        logger.info(f"Logged in as {self.user}")
        logger.info("------")

# Initialize bot with all intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = Bot(command_prefix=PREFIX, intents=intents)  # Using our custom Bot class

# Gestione della chiusura
def signal_handler(sig, frame):
    logger.info("Segnale di chiusura ricevuto")
    asyncio.run(bot.close())
    sys.exit(0)

# Registra il gestore per SIGINT (Ctrl+C) e SIGTERM
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Carica i cog
async def load_extensions():
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py'):
            await bot.load_extension(f'cogs.{filename[:-3]}')
            logger.info(f"Caricato cog: {filename[:-3]}")

@bot.event
async def on_message(message):
    # Ignora i messaggi del bot stesso
    if message.author == bot.user:
        return

    # Log user message
    extra = {
        'user': str(message.author),
        'user_id': message.author.id,
        'channel': message.channel.name,
        'channel_id': message.channel.id,
        'guild': message.guild.name if message.guild else 'DM',
        'guild_id': message.guild.id if message.guild else None,
        'message_id': message.id,
        'reference': message.reference.message_id if message.reference else None,
        'created_at': message.created_at.isoformat(),
        'edited_at': message.edited_at.isoformat() if message.edited_at else None,
        'is_system': message.is_system(),
        'is_pinned': message.pinned,
        'type': str(message.type),
        'thread_info': {
            'id': message.channel.id,
            'name': message.channel.name
        } if isinstance(message.channel, discord.Thread) else None,
        'mentions': {
            'users': [str(user) for user in message.mentions],
            'roles': [str(role) for role in message.role_mentions],
            'everyone': message.mention_everyone
        },
        'embeds': len(message.embeds),
        'reactions': [str(reaction) for reaction in message.reactions],
        'flags': message.flags.value if message.flags else 0
    }
    
    # Create a copy of the logger with extra fields
    logger_with_context = logging.LoggerAdapter(user_logger, extra)
    
    # Log the message content with additional context
    log_message = message.content
    if message.reference:
        log_message += f" (Reply to: {message.reference.message_id})"
    if message.attachments:
        log_message += f" [Attachments: {[att.filename for att in message.attachments]}]"
    
    logger_with_context.info(log_message)

    # Process commands normalmente
    await bot.process_commands(message)

    # --- AGGIUNTA: intercetta <argomento> !topic o !draft ---
    content = message.content.strip()
    lowered = content.lower()
    for cmd in ["!topic", "!draft"]:
        if lowered.endswith(cmd):
            # Prendi l'argomento (tutto ciò che precede il comando)
            arg = content[:-len(cmd)].strip()
            if arg:
                # Ricostruisci il messaggio come !comando <argomento>
                fake_content = f"{cmd} {arg}"
                # Crea una copia del messaggio con il nuovo contenuto
                fake_message = message
                fake_message.content = fake_content
                ctx = await bot.get_context(fake_message)
                await bot.invoke(ctx)
            break

def handle_exception(loop, context):
    """Custom exception handler"""
    # Ignore cancelled errors during shutdown
    if isinstance(context.get('exception'), asyncio.CancelledError):
        return
    
    # Ignore connection reset errors during shutdown
    msg = context.get('message', '')
    if "Connection reset by peer" in msg:
        return
        
    # Log other unhandled exceptions
    logger.error(f"Unhandled exception: {msg}")

async def shutdown(loop):
    """Clean shutdown of the bot and all tasks"""
    if getattr(bot, 'is_shutting_down', False):
        return
        
    logger.info('Initiating shutdown')
    bot.is_shutting_down = True
    
    try:
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        
        if tasks:
            logger.info(f'Cancelling {len(tasks)} outstanding tasks')
            for task in tasks:
                if not task.done():
                    task.cancel()
            
            # Wait for tasks to complete with configured timeout
            try:
                await asyncio.wait(tasks, timeout=bot.config['bot']['shutdown_timeout'])
            except asyncio.TimeoutError:
                pass
            
        if not bot.is_closed():
            await bot.close()
            
    except Exception as e:
        logger.error(f'Error during shutdown: {e}')
    finally:
        logger.info('Shutdown complete')
        cleanup_lock()  # Final cleanup

async def main():
    loop = asyncio.get_event_loop()
    
    try:
        def handle_shutdown_signal(sig):
            if not bot.is_shutting_down:
                asyncio.create_task(shutdown(loop))
        
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(
                sig,
                lambda s=sig: handle_shutdown_signal(s)
            )
        
        # Set custom exception handler
        loop.set_exception_handler(handle_exception)
        
        # Load extensions and start the bot
        await load_extensions()
        await bot.start(TOKEN)
        
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    except Exception as e:
        logger.error(f'Fatal error: {str(e)}')
    finally:
        if not loop.is_closed():
            await shutdown(loop)

if __name__ == "__main__":
    try:
        # Check for other instances before starting
        check_running()
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Chiusura forzata del bot")
        asyncio.run(bot.close())
    except Exception as e:
        logger.error(f"Errore durante l'esecuzione del bot: {str(e)}")
        asyncio.run(bot.close())
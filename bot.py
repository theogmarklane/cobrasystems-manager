import discord
from discord.ext import commands
import os
import json
import asyncio
import logging
from dotenv import load_dotenv
from keep_alive import start_background

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
MONGO_URI = os.getenv("MONGO_URI")

# Load config
def load_config():
    with open("config.json", "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(data):
    with open("config.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

config = load_config()

# Install a safe logging formatter/handler to avoid formatting crashes from library logs
class _SafeFormatter(logging.Formatter):
    def format(self, record):
        try:
            return super().format(record)
        except Exception:
            # Best-effort fallback to avoid crashing logging in background threads
            try:
                message = record.getMessage()
            except Exception:
                message = str(record.msg)
            time = self.formatTime(record, self.datefmt) if hasattr(self, 'formatTime') else ''
            return f"{time} {record.levelname}: {message}"

root_logger = logging.getLogger()
# Ensure all handlers use the safe formatter to avoid formatting crashes; add a stream handler if none exist
safe_fmt = _SafeFormatter("%(asctime)s %(levelname)s: %(message)s")
if root_logger.handlers:
    for h in list(root_logger.handlers):
        try:
            h.setFormatter(safe_fmt)
        except Exception:
            pass
else:
    handler = logging.StreamHandler()
    handler.setFormatter(safe_fmt)
    root_logger.addHandler(handler)
root_logger.setLevel(logging.INFO)

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.guilds = True
intents.reactions = True
intents.moderation = True

bot = commands.Bot(
    command_prefix=commands.when_mentioned_or(config.get("prefix", "!")),
    intents=intents,
    owner_id=OWNER_ID,
    help_command=None,  # We'll make a custom one
    case_insensitive=True
)

# Initialize MongoDB if provided
if MONGO_URI:
    try:
        import motor.motor_asyncio
        # naive parse for DB name; use last path segment or default
        db_name = MONGO_URI.rsplit("/", 1)[-1] or "ProjectSHDW"
        mongo_client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
        bot.db = mongo_client[db_name]
        print(f"✅ Connected to MongoDB database: {db_name}")
    except Exception as e:
        print(f"❌ Failed to initialize MongoDB: {e}")

bot.config = config
bot.save_config = lambda: save_config(bot.config)
bot.embed_color = config.get("embed_color", 0x00FF9F)
bot.footer = config.get("footer", "Cobra Systems™ Manager")

_original_context_send = commands.Context.send


async def send_with_fake_embed(self, *args, **kwargs):
    """Show a short-lived placeholder embed before the real command response."""
    bypass_fake = kwargs.pop("bypass_fake", False)
    if bypass_fake:
        return await _original_context_send(self, *args, **kwargs)

    fake_embed = discord.Embed(
        title="🐍 Cobra Systems™ Manager",
        description="Working on it...",
        color=0x2B2D31,
    )

    temp_message = None
    try:
        if getattr(self, "interaction", None) is not None and not self.interaction.response.is_done():
            try:
                await self.interaction.response.defer(thinking=True)
            except discord.HTTPException:
                pass

        temp_message = await self.channel.send(embed=fake_embed)
        await asyncio.sleep(0.35)
        await temp_message.delete()
    except Exception:
        pass

    return await _original_context_send(self, *args, **kwargs)


commands.Context.send = send_with_fake_embed


async def send_response(ctx, **kwargs):
    """Send a response that works for both prefix and hybrid command interactions."""
    interaction = getattr(ctx, "interaction", None)

    if interaction is None:
        return await ctx.send(**kwargs)

    try:
        if interaction.response.is_done():
            return await interaction.followup.send(**kwargs)
        return await interaction.response.send_message(**kwargs)
    except (discord.NotFound, discord.HTTPException):
        fallback_kwargs = dict(kwargs)
        fallback_kwargs.pop("ephemeral", None)
        return await ctx.channel.send(**fallback_kwargs)

async def load_cogs():
    cogs = [
        "cogs.events",
        "cogs.moderation",
            "cogs.audit_logs",
        "cogs.roles",
        "cogs.utility",
        "cogs.admin",
        "cogs.automod",
        "cogs.economy",
        "cogs.leveling",
        "cogs.polls",
        "cogs.starboard",
        "cogs.giveaways",
        "cogs.tags",
        "cogs.backup",
        "cogs.stats",
        "cogs.fun",
        "cogs.honeypot",
        "cogs.tickets",
        "cogs.yt_notifications",
    ]
    for cog in cogs:
        try:
            await bot.load_extension(cog)
            print(f"✅ Loaded {cog}")
        except Exception as e:
            print(f"❌ Failed to load {cog}: {e}")

@bot.event
async def setup_hook():
    # If MongoDB is available, attempt to load global config from DB
    if hasattr(bot, "db"):
        try:
            coll = bot.db["config"]
            doc = await coll.find_one({"_id": "global"})
            if doc and isinstance(doc.get("data"), dict):
                bot.config = doc["data"]
                print("✅ Loaded config from MongoDB")
            else:
                # write current file config to DB as baseline
                await coll.update_one({"_id": "global"}, {"$set": {"data": bot.config}}, upsert=True)
                print("✅ Initialized config in MongoDB from file")
        except Exception as e:
            print(f"❌ Failed to load config from MongoDB: {e}")

    # Provide a save_config helper that writes to DB when available
    async def _save_config_db(data):
        try:
            await bot.db["config"].update_one({"_id": "global"}, {"$set": {"data": data}}, upsert=True)
        except Exception as e:
            print(f"❌ Failed to save config to DB: {e}")

    def save_config_generic():
        if hasattr(bot, "db"):
            asyncio.create_task(_save_config_db(bot.config))
        else:
            save_config(bot.config)

    bot.save_config = save_config_generic

    await load_cogs()
    # Register every loaded hybrid command. Guild sync is immediate and is
    # useful in Docker/development; global sync is kept for all other servers.
    try:
        guild_id = os.getenv("DISCORD_GUILD_ID")
        if guild_id:
            guild = discord.Object(id=int(guild_id))
            bot.tree.copy_global_to(guild=guild)
            synced = await bot.tree.sync(guild=guild)
            print(f"✅ Preloaded {len(synced)} slash command(s) to guild {guild_id}")
        else:
            synced = await bot.tree.sync()
            print(f"✅ Synced {len(synced)} global slash command(s)")
    except Exception as e:
        print(f"❌ Failed to sync commands: {e}")

@bot.event
async def on_ready():
    print(f"""
╔══════════════════════════════════════════════╗
║   Cobra Systems™ Manager is online!          ║
║   Logged in as: {bot.user}                   
║   ID: {bot.user.id}                          
║   Servers: {len(bot.guilds)}                 
╚══════════════════════════════════════════════╝
    """)
    # Set presence status without a visible activity. Use config key "status" or env BOT_STATUS.
    status_str = bot.config.get("status", os.getenv("BOT_STATUS", "dnd")).lower()
    status_map = {
        "online": discord.Status.online,
        "idle": discord.Status.idle,
        "dnd": discord.Status.dnd,
        "invisible": discord.Status.invisible,
    }
    status = status_map.get(status_str, discord.Status.dnd)
    try:
        await bot.change_presence(status=status)
    except Exception:
        # Fallback: set to dnd if anything goes wrong
        try:
            await bot.change_presence(status=discord.Status.dnd)
        except Exception:
            pass

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.MissingPermissions):
        embed = discord.Embed(
            title="⛔ Missing Permissions",
            description="You don't have the required permissions to use this command.",
            color=0xFF0000
        )
        await send_response(ctx, embed=embed, ephemeral=True if getattr(ctx, "interaction", None) else False)
        return
    if isinstance(error, commands.BotMissingPermissions):
        embed = discord.Embed(
            title="⛔ Bot Missing Permissions",
            description="I don't have the required permissions to do that.",
            color=0xFF0000
        )
        await send_response(ctx, embed=embed)
        return
    if isinstance(error, commands.MissingRequiredArgument):
        embed = discord.Embed(
            title="⚠️ Missing Argument",
            description=f"Missing required argument: `{error.param.name}`",
            color=0xFFAA00
        )
        await send_response(ctx, embed=embed)
        return
    # Generic
    print(f"Error in {ctx.command}: {error}")
    embed = discord.Embed(
        title="❌ Error",
        description=str(error),
        color=0xFF0000
    )
    await send_response(ctx, embed=embed)

if __name__ == "__main__":
    if not TOKEN:
        print("❌ No DISCORD_TOKEN found in .env file!")
    else:
        # Start simple keep-alive webserver so hosting providers don't put the process to sleep
        try:
            port = int(os.getenv("PORT", "8080"))
            start_background(port=port)
            print(f"✅ Keep-alive server started on port {port}")
        except Exception:
            pass
        bot.run(TOKEN)
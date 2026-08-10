import discord
from discord.ext import commands
import os
import json
import asyncio
from dotenv import load_dotenv

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
        "cogs.tickets",
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
    # Sync slash commands
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash command(s)")
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
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="your server 🐍 | /help"
        )
    )

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
        bot.run(TOKEN)
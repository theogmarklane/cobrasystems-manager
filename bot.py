import discord
from discord.ext import commands
import os
import json
import asyncio
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

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

bot.config = config
bot.save_config = lambda: save_config(bot.config)
bot.embed_color = config.get("embed_color", 0x00FF9F)
bot.footer = config.get("footer", "Cobra Systems™ Manager")

async def load_cogs():
    cogs = [
        "cogs.events",
        "cogs.moderation",
        "cogs.roles",
        "cogs.utility",
    ]
    for cog in cogs:
        try:
            await bot.load_extension(cog)
            print(f"✅ Loaded {cog}")
        except Exception as e:
            print(f"❌ Failed to load {cog}: {e}")

@bot.event
async def setup_hook():
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
        await ctx.send(embed=embed, ephemeral=True if hasattr(ctx, "interaction") and ctx.interaction else False)
        return
    if isinstance(error, commands.BotMissingPermissions):
        embed = discord.Embed(
            title="⛔ Bot Missing Permissions",
            description="I don't have the required permissions to do that.",
            color=0xFF0000
        )
        await ctx.send(embed=embed)
        return
    if isinstance(error, commands.MissingRequiredArgument):
        embed = discord.Embed(
            title="⚠️ Missing Argument",
            description=f"Missing required argument: `{error.param.name}`",
            color=0xFFAA00
        )
        await ctx.send(embed=embed)
        return
    # Generic
    print(f"Error in {ctx.command}: {error}")
    embed = discord.Embed(
        title="❌ Error",
        description=str(error),
        color=0xFF0000
    )
    await ctx.send(embed=embed)

if __name__ == "__main__":
    if not TOKEN:
        print("❌ No DISCORD_TOKEN found in .env file!")
    else:
        bot.run(TOKEN)
import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
import json

class Backup(commands.Cog):
    """Simple backup/export commands for config and data."""
    def __init__(self, bot):
        self.bot = bot

    def get_embed(self, title: str, description: str = None, color=None):
        embed = discord.Embed(title=title, description=description, color=color or self.bot.embed_color, timestamp=datetime.utcnow())
        embed.set_footer(text=self.bot.footer)
        return embed

    @commands.has_permissions(administrator=True)
    @commands.hybrid_command(name="export_all", description="Export full config/data to a file (admin)")
    async def export_all(self, ctx: commands.Context):
        data = {}
        if hasattr(self.bot, "db"):
            # export some collections
            for name in ["config", "reaction_roles", "warnings", "reminders"]:
                try:
                    docs = await self.bot.db[name].find({}).to_list(length=None)
                    data[name] = docs
                except Exception:
                    data[name] = []
        else:
            # read config file
            try:
                with open("config.json", "r", encoding="utf-8") as f:
                    data["config"] = json.load(f)
            except Exception:
                data["config"] = {}
        filename = f"backup_{int(datetime.utcnow().timestamp())}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        await ctx.send(embed=self.get_embed("✅ Exported", f"Backup written to `{filename}`"))

async def setup(bot):
    await bot.add_cog(Backup(bot))

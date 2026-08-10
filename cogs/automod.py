import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime

class Automod(commands.Cog):
    """Simple automod with blacklist and invite/link filtering. Stores settings in Mongo if available."""
    def __init__(self, bot):
        self.bot = bot

    def get_embed(self, title: str, description: str = None, color=None):
        embed = discord.Embed(title=title, description=description, color=color or self.bot.embed_color, timestamp=datetime.utcnow())
        embed.set_footer(text=self.bot.footer)
        return embed

    @commands.hybrid_command(name="setfilter", description="Enable/disable invite/link filter")
    @commands.has_permissions(manage_guild=True)
    async def setfilter(self, ctx: commands.Context, enabled: bool):
        guild_id = str(ctx.guild.id)
        if hasattr(self.bot, "db"):
            await self.bot.db["automod_settings"].update_one({"guild_id": guild_id}, {"$set": {"filter": enabled}}, upsert=True)
        else:
            cfg = self.bot.config.setdefault("automod", {})
            cfg[guild_id] = {"filter": enabled}
            self.bot.save_config()
        await ctx.send(embed=self.get_embed("✅ Updated", f"Filter set to {enabled}"))

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        guild_id = str(message.guild.id)
        enabled = False
        if hasattr(self.bot, "db"):
            doc = await self.bot.db["automod_settings"].find_one({"guild_id": guild_id})
            enabled = bool(doc and doc.get("filter"))
        else:
            enabled = bool(self.bot.config.get("automod", {}).get(guild_id, {}).get("filter"))
        if not enabled:
            return
        # basic invite/link check
        if "discord.gg/" in message.content.lower() or "https://discord.gg/" in message.content.lower() or "http://" in message.content.lower():
            try:
                await message.delete()
                await message.channel.send(embed=self.get_embed("🚫 Link Removed", f"{message.author.mention}, links are not allowed here."))
            except Exception:
                pass

async def setup(bot):
    await bot.add_cog(Automod(bot))

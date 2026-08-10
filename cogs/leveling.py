import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
import random

class Leveling(commands.Cog):
    """Basic leveling system: awards XP per message and allows checking level."""
    def __init__(self, bot):
        self.bot = bot

    def get_embed(self, title: str, description: str = None, color=None):
        embed = discord.Embed(title=title, description=description, color=color or self.bot.embed_color, timestamp=datetime.utcnow())
        embed.set_footer(text=self.bot.footer)
        return embed

    async def _add_xp(self, user_id: str, amount: int):
        if hasattr(self.bot, "db"):
            doc = await self.bot.db["levels"].find_one({"user_id": user_id})
            if not doc:
                await self.bot.db["levels"].insert_one({"user_id": user_id, "xp": amount})
            else:
                await self.bot.db["levels"].update_one({"user_id": user_id}, {"$inc": {"xp": amount}})
        else:
            cfg = self.bot.config.setdefault("levels", {})
            cfg[user_id] = cfg.get(user_id, 0) + amount
            self.bot.save_config()

    async def _get_xp(self, user_id: str):
        if hasattr(self.bot, "db"):
            doc = await self.bot.db["levels"].find_one({"user_id": user_id})
            return doc.get("xp", 0) if doc else 0
        else:
            return self.bot.config.get("levels", {}).get(user_id, 0)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        # small chance to award xp to reduce spam
        if random.random() < 0.35:
            xp = random.randint(5, 15)
            await self._add_xp(str(message.author.id), xp)

    @commands.hybrid_command(name="level", description="Show a member's XP/level")
    async def level(self, ctx: commands.Context, member: discord.Member = None):
        member = member or ctx.author
        xp = await self._get_xp(str(member.id))
        level = int((xp // 100) ** 0.5 * 10)  # simple progression
        await ctx.send(embed=self.get_embed("📈 Level", f"{member.mention}: Level **{level}** • XP **{xp}**"))

async def setup(bot):
    await bot.add_cog(Leveling(bot))

import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime

class Economy(commands.Cog):
    """Simple economy: balance, give, and daily."""
    def __init__(self, bot):
        self.bot = bot

    def get_embed(self, title: str, description: str = None, color=None):
        embed = discord.Embed(title=title, description=description, color=color or self.bot.embed_color, timestamp=datetime.utcnow())
        embed.set_footer(text=self.bot.footer)
        return embed

    async def _get_balance(self, user_id: str):
        if hasattr(self.bot, "db"):
            doc = await self.bot.db["economy"].find_one({"user_id": user_id})
            return doc.get("balance", 0) if doc else 0
        else:
            return self.bot.config.setdefault("economy", {}).get(user_id, 0)

    async def _set_balance(self, user_id: str, amount: int):
        if hasattr(self.bot, "db"):
            await self.bot.db["economy"].update_one({"user_id": user_id}, {"$set": {"balance": amount}}, upsert=True)
        else:
            self.bot.config.setdefault("economy", {})[user_id] = amount
            self.bot.save_config()

    @commands.hybrid_command(name="balance", description="Check your balance")
    async def balance(self, ctx: commands.Context, member: discord.Member = None):
        member = member or ctx.author
        bal = await self._get_balance(str(member.id))
        await ctx.send(embed=self.get_embed("💰 Balance", f"{member.mention} has **{bal}** coins."))

    @commands.hybrid_command(name="give", description="Give coins to another user")
    async def give(self, ctx: commands.Context, member: discord.Member, amount: int):
        if amount <= 0:
            return await ctx.send(embed=self.get_embed("⚠️ Invalid", "Amount must be positive.", 0xFFAA00))
        user_id = str(ctx.author.id)
        target_id = str(member.id)
        bal = await self._get_balance(user_id)
        if bal < amount:
            return await ctx.send(embed=self.get_embed("⚠️ Insufficient", "You don't have enough coins.", 0xFFAA00))
        await self._set_balance(user_id, bal - amount)
        targ_bal = await self._get_balance(target_id)
        await self._set_balance(target_id, targ_bal + amount)
        await ctx.send(embed=self.get_embed("✅ Sent", f"Sent **{amount}** coins to {member.mention}."))

    @commands.hybrid_command(name="daily", description="Claim your daily coins")
    async def daily(self, ctx: commands.Context):
        uid = str(ctx.author.id)
        if hasattr(self.bot, "db"):
            doc = await self.bot.db["economy"].find_one({"user_id": uid})
            last = doc.get("last_daily", 0) if doc else 0
            bal = doc.get("balance", 0) if doc else 0
            now = int(datetime.utcnow().timestamp())
            if now - last < 86400:
                return await ctx.send(embed=self.get_embed("⏳ Wait", "You can only claim daily once every 24 hours.", 0xFFAA00))
            bal += 100
            await self.bot.db["economy"].update_one({"user_id": uid}, {"$set": {"balance": bal, "last_daily": now}}, upsert=True)
            await ctx.send(embed=self.get_embed("✅ Claimed", "You claimed **100** coins."))
        else:
            cfg = self.bot.config.setdefault("economy", {})
            ent = cfg.setdefault(uid, {"balance": 0, "last_daily": 0})
            now = int(datetime.utcnow().timestamp())
            if now - ent.get("last_daily", 0) < 86400:
                return await ctx.send(embed=self.get_embed("⏳ Wait", "You can only claim daily once every 24 hours.", 0xFFAA00))
            ent["balance"] = ent.get("balance", 0) + 100
            ent["last_daily"] = now
            self.bot.save_config()
            await ctx.send(embed=self.get_embed("✅ Claimed", "You claimed **100** coins."))

async def setup(bot):
    await bot.add_cog(Economy(bot))

import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime

class Stats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_embed(self, title: str, description: str = None, color=None):
        embed = discord.Embed(title=title, description=description, color=color or self.bot.embed_color, timestamp=datetime.utcnow())
        embed.set_footer(text=self.bot.footer)
        return embed

    @commands.hybrid_command(name="serverstats", description="Show server statistics")
    async def serverstats(self, ctx: commands.Context):
        g = ctx.guild
        text = f"Members: {g.member_count}\nChannels: {len(g.channels)}\nRoles: {len(g.roles)}\nBoosts: {g.premium_subscription_count or 0}"
        await ctx.send(embed=self.get_embed("📊 Server Stats", text))

async def setup(bot):
    await bot.add_cog(Stats(bot))

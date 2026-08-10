import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime

class Starboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_embed(self, title: str, description: str = None, color=None):
        embed = discord.Embed(title=title, description=description, color=color or self.bot.embed_color, timestamp=datetime.utcnow())
        embed.set_footer(text=self.bot.footer)
        return embed

    @commands.hybrid_command(name="setstarboard", description="Set the starboard channel")
    @commands.has_permissions(manage_guild=True)
    async def setstarboard(self, ctx: commands.Context, channel: discord.TextChannel = None):
        gid = str(ctx.guild.id)
        if channel is None:
            # disable
            if hasattr(self.bot, "db"):
                await self.bot.db["starboard"].delete_one({"guild_id": gid})
            else:
                self.bot.config.setdefault("starboard", {}).pop(gid, None)
                self.bot.save_config()
            return await ctx.send(embed=self.get_embed("✅ Disabled", "Starboard disabled."))
        if hasattr(self.bot, "db"):
            await self.bot.db["starboard"].update_one({"guild_id": gid}, {"$set": {"channel_id": channel.id}}, upsert=True)
        else:
            self.bot.config.setdefault("starboard", {})[gid] = channel.id
            self.bot.save_config()
        await ctx.send(embed=self.get_embed("✅ Set", f"Starboard set to {channel.mention}"))

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id:
            return
        if str(payload.emoji) != "⭐":
            return
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return
        gid = str(guild.id)
        if hasattr(self.bot, "db"):
            doc = await self.bot.db["starboard"].find_one({"guild_id": gid})
            channel_id = doc.get("channel_id") if doc else None
        else:
            channel_id = self.bot.config.get("starboard", {}).get(gid)
        if not channel_id:
            return
        channel = guild.get_channel(channel_id)
        if not channel:
            return
        # fetch message
        try:
            channel_src = guild.get_channel(payload.channel_id)
            msg = await channel_src.fetch_message(payload.message_id)
            embed = self.get_embed(f"⭐ Starred in {channel_src.name}", msg.content)
            embed.set_author(name=msg.author.display_name, icon_url=msg.author.display_avatar.url)
            embed.add_field(name="Jump", value=f"[Jump to message]({msg.jump_url})")
            await channel.send(embed=embed)
        except Exception:
            pass

async def setup(bot):
    await bot.add_cog(Starboard(bot))

import discord
from discord.ext import commands
import asyncio


class Honeypot(commands.Cog):
    """If a member sends any message in a configured honeypot channel,
    they will be banned and their messages removed across the guild."""

    def __init__(self, bot):
        self.bot = bot

    def get_honeypot_channel(self, guild_id: str):
        honeypots = self.bot.config.get("honeypot_channel", {})
        return honeypots.get(guild_id)

    @commands.hybrid_command(name="sethoneypot", description="Set or clear this server's honeypot channel")
    @commands.has_permissions(administrator=True)
    async def set_honeypot(self, ctx, channel: discord.TextChannel = None):
        """Set the honeypot channel for this guild. Use without args to clear."""
        gid = str(ctx.guild.id)
        if channel is None:
            self.bot.config.setdefault("honeypot_channel", {}).pop(gid, None)
            self.bot.save_config()
            await ctx.send(f"Honeypot cleared for this server.")
            return

        self.bot.config.setdefault("honeypot_channel", {})[gid] = channel.id
        self.bot.save_config()
        await ctx.send(f"Honeypot set to {channel.mention}. Anyone who speaks there will be banned and their messages removed.")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.guild is None:
            return

        gid = str(message.guild.id)
        hp = self.get_honeypot_channel(gid)
        if not hp:
            return

        if message.channel.id != hp:
            return

        # At this point someone spoke in the honeypot
        member = message.author

        try:
            # delete the triggering message first
            await message.delete()
        except Exception:
            pass

        # Attempt to remove messages across channels
        async def purge_user_messages(channel):
            try:
                if not isinstance(channel, (discord.TextChannel, discord.Thread)):
                    return
                if not channel.permissions_for(message.guild.me).manage_messages:
                    return
                await channel.purge(limit=10000, check=lambda m: m.author.id == member.id)
            except Exception:
                return

        tasks = []
        for ch in message.guild.channels:
            tasks.append(purge_user_messages(ch))

        # Run purges concurrently but don't block too long
        try:
            await asyncio.gather(*tasks)
        except Exception:
            pass

        # Finally, ban the user
        try:
            await message.guild.ban(member, reason="Honeypot triggered", delete_message_days=0)
        except Exception:
            pass


async def setup(bot):
    await bot.add_cog(Honeypot(bot))

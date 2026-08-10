import discord
from discord.ext import commands
from datetime import datetime

class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_embed(self, title: str, description: str = None, color=None):
        embed = discord.Embed(
            title=title,
            description=description,
            color=color or self.bot.embed_color,
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text=self.bot.footer)
        return embed

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild = member.guild
        guild_id = str(guild.id)

        # Auto Role
        auto_roles = self.bot.config.get("auto_role", {})
        if guild_id in auto_roles:
            role_id = auto_roles[guild_id]
            role = guild.get_role(role_id)
            if role:
                try:
                    await member.add_roles(role, reason="Auto Role")
                except discord.Forbidden:
                    pass

        # Welcome Message
        welcome_channels = self.bot.config.get("welcome_channel", {})
        if guild_id in welcome_channels:
            channel = guild.get_channel(welcome_channels[guild_id])
            if channel:
                embed = self.get_embed(
                    title=f"Welcome to {guild.name}!",
                    description=(
                        f"Hey {member.mention}! Welcome to **{guild.name}**.\n\n"
                        f"You are member **#{guild.member_count}**.\n"
                        f"Make sure to read the rules and have fun!"
                    )
                )
                embed.set_thumbnail(url=member.display_avatar.url)
                if guild.icon:
                    embed.set_author(name=guild.name, icon_url=guild.icon.url)
                try:
                    await channel.send(embed=embed)
                except discord.Forbidden:
                    pass

        # Log
        await self.log_action(
            guild,
            f"Member Joined",
            f"{member.mention} (`{member.id}`)\nAccount created: <t:{int(member.created_at.timestamp())}:R>"
        )

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        await self.log_action(
            member.guild,
            "Member Left",
            f"{member} (`{member.id}`)"
        )

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        await self.log_action(
            guild,
            "Member Banned",
            f"{user} (`{user.id}`)"
        )

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User):
        await self.log_action(
            guild,
            "Member Unbanned",
            f"{user} (`{user.id}`)"
        )

    async def log_action(self, guild: discord.Guild, title: str, description: str):
        log_channels = self.bot.config.get("log_channel", {})
        channel_id = log_channels.get(str(guild.id))
        if not channel_id:
            return
        channel = guild.get_channel(channel_id)
        if not channel:
            return
        embed = self.get_embed(title=title, description=description, color=0x5865F2)
        try:
            await channel.send(embed=embed)
        except discord.Forbidden:
            pass

async def setup(bot):
    await bot.add_cog(Events(bot))
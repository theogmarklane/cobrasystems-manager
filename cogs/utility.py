import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
import platform
import time

class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = time.time()

    def get_embed(self, title: str, description: str = None, color=None):
        embed = discord.Embed(
            title=title,
            description=description,
            color=color or self.bot.embed_color,
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text=self.bot.footer)
        return embed

    # ==================== HELP ====================
    @commands.hybrid_command(name="help", description="Show all available commands")
    async def help(self, ctx: commands.Context):
        embed = self.get_embed(
            "🐍 Cobra Systems™ Manager — Help",
            "A powerful server management bot.\nUse `/command` or `!command`."
        )

        embed.add_field(
            name="🛡️ Moderation",
            value=(
                "`ban` `unban` `kick`\n"
                "`mute` / `timeout` `unmute`\n"
                "`warn` `warnings` `clearwarns`\n"
                "`purge` `lock` `unlock` `slowmode`"
            ),
            inline=True
        )
        embed.add_field(
            name="🎭 Roles & Setup",
            value=(
                "`autorole` `welcome` `setlog`\n"
                "`reactionrole` / `rr`\n"
                "`removereactionrole`\n"
                "`giverole` `takerole`"
            ),
            inline=True
        )
        embed.add_field(
            name="🔧 Utility",
            value=(
                "`help` `ping` `uptime`\n"
                "`userinfo` `serverinfo`\n"
                "`avatar` `roleinfo`"
            ),
            inline=True
        )

        embed.add_field(
            name="📌 Quick Setup",
            value=(
                "1. `/setlog #mod-logs` — Enable logging\n"
                "2. `/welcome #welcome` — Welcome messages\n"
                "3. `/autorole @Member` — Auto role on join\n"
                "4. `/reactionrole` — Create reaction roles"
            ),
            inline=False
        )

        await ctx.send(embed=embed)

    # ==================== PING ====================
    @commands.hybrid_command(name="ping", description="Check the bot's latency")
    async def ping(self, ctx: commands.Context):
        latency = round(self.bot.latency * 1000)
        embed = self.get_embed("🏓 Pong!", f"Latency: **{latency}ms**")
        await ctx.send(embed=embed)

    # ==================== UPTIME ====================
    @commands.hybrid_command(name="uptime", description="Show how long the bot has been online")
    async def uptime(self, ctx: commands.Context):
        seconds = int(time.time() - self.start_time)
        days, remainder = divmod(seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{days}d {hours}h {minutes}m {seconds}s"
        embed = self.get_embed("⏱️ Uptime", f"Online for **{uptime_str}**")
        await ctx.send(embed=embed)

    # ==================== USERINFO ====================
    @commands.hybrid_command(name="userinfo", description="Get information about a user", aliases=["ui", "whois"])
    @app_commands.describe(member="The member to lookup (defaults to you)")
    async def userinfo(self, ctx: commands.Context, member: discord.Member = None):
        member = member or ctx.author
        roles = [r.mention for r in member.roles if r != ctx.guild.default_role]
        roles_str = ", ".join(roles[::-1][:10]) if roles else "None"
        if len(roles) > 10:
            roles_str += f" (+{len(roles)-10} more)"

        embed = self.get_embed(f"User Info — {member}")
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="ID", value=member.id, inline=True)
        embed.add_field(name="Nickname", value=member.nick or "None", inline=True)
        embed.add_field(name="Bot", value="Yes" if member.bot else "No", inline=True)
        embed.add_field(name="Account Created", value=f"<t:{int(member.created_at.timestamp())}:R>", inline=True)
        embed.add_field(name="Joined Server", value=f"<t:{int(member.joined_at.timestamp())}:R>" if member.joined_at else "Unknown", inline=True)
        embed.add_field(name="Top Role", value=member.top_role.mention, inline=True)
        embed.add_field(name=f"Roles [{len(roles)}]", value=roles_str or "None", inline=False)

        if member.timed_out_until:
            embed.add_field(name="Timed Out Until", value=f"<t:{int(member.timed_out_until.timestamp())}:R>", inline=False)

        await ctx.send(embed=embed)

    # ==================== SERVERINFO ====================
    @commands.hybrid_command(name="serverinfo", description="Get information about the server", aliases=["si", "guildinfo"])
    async def serverinfo(self, ctx: commands.Context):
        guild = ctx.guild
        embed = self.get_embed(f"Server Info — {guild.name}")
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        embed.add_field(name="Owner", value=guild.owner.mention if guild.owner else "Unknown", inline=True)
        embed.add_field(name="ID", value=guild.id, inline=True)
        embed.add_field(name="Created", value=f"<t:{int(guild.created_at.timestamp())}:R>", inline=True)
        embed.add_field(name="Members", value=guild.member_count, inline=True)
        embed.add_field(name="Channels", value=len(guild.channels), inline=True)
        embed.add_field(name="Roles", value=len(guild.roles), inline=True)
        embed.add_field(name="Boost Level", value=guild.premium_tier, inline=True)
        embed.add_field(name="Boosts", value=guild.premium_subscription_count or 0, inline=True)
        embed.add_field(name="Verification", value=str(guild.verification_level).title(), inline=True)

        await ctx.send(embed=embed)

    # ==================== AVATAR ====================
    @commands.hybrid_command(name="avatar", description="Get a user's avatar", aliases=["av", "pfp"])
    @app_commands.describe(member="The member (defaults to you)")
    async def avatar(self, ctx: commands.Context, member: discord.Member = None):
        member = member or ctx.author
        embed = self.get_embed(f"Avatar — {member}")
        embed.set_image(url=member.display_avatar.url)
        await ctx.send(embed=embed)

    # ==================== ROLEINFO ====================
    @commands.hybrid_command(name="roleinfo", description="Get information about a role")
    @app_commands.describe(role="The role to lookup")
    async def roleinfo(self, ctx: commands.Context, role: discord.Role):
        embed = self.get_embed(f"Role Info — {role.name}")
        embed.color = role.color if role.color.value != 0 else self.bot.embed_color
        embed.add_field(name="ID", value=role.id, inline=True)
        embed.add_field(name="Color", value=str(role.color), inline=True)
        embed.add_field(name="Position", value=role.position, inline=True)
        embed.add_field(name="Members", value=len(role.members), inline=True)
        embed.add_field(name="Mentionable", value="Yes" if role.mentionable else "No", inline=True)
        embed.add_field(name="Hoisted", value="Yes" if role.hoist else "No", inline=True)
        embed.add_field(name="Created", value=f"<t:{int(role.created_at.timestamp())}:R>", inline=True)
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Utility(bot))
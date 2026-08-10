import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
import platform
import time
import os
import json
import uuid
import asyncio

REMINDERS_FILE = "data/reminders.json"

class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = time.time()
        self.use_db = hasattr(bot, "db")
        self.reminders = {} if self.use_db else self.load_reminders()
        # start background reminder loop
        try:
            self.bot.loop.create_task(self._reminder_loop())
        except Exception:
            pass

    def get_embed(self, title: str, description: str = None, color=None):
        embed = discord.Embed(
            title=title,
            description=description,
            color=color or self.bot.embed_color,
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text=self.bot.footer)
        return embed

    def load_reminders(self):
        if not os.path.exists(REMINDERS_FILE):
            return {}
        try:
            with open(REMINDERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}

    def save_reminders(self):
        os.makedirs("data", exist_ok=True)
        with open(REMINDERS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.reminders, f, indent=2)

    def _parse_duration(self, text: str):
        units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
        try:
            amount = int(text[:-1])
            unit = text[-1].lower()
            return amount * units[unit]
        except Exception:
            return None

    async def _reminder_loop(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            now = int(time.time())
            # If using DB, pull due reminders from collection; otherwise use local store
            if self.use_db:
                try:
                    coll = self.bot.db["reminders"]
                    docs = await coll.find({"timestamp": {"$lte": now}}).to_list(length=None)
                    for d in docs:
                        try:
                            user = await self.bot.fetch_user(int(d.get("user_id")))
                            msg = d.get("message", "Reminder")
                            embed = self.get_embed("⏰ Reminder", msg)
                            await user.send(embed=embed)
                        except Exception:
                            pass
                        # remove delivered reminder
                        await coll.delete_one({"_id": d.get("_id")})
                except Exception:
                    pass
            else:
                changed = False
                for user_id, items in list(self.reminders.items()):
                    for r in list(items):
                        if r.get("timestamp") <= now:
                            try:
                                user = await self.bot.fetch_user(int(user_id))
                                msg = r.get("message", "Reminder")
                                embed = self.get_embed("⏰ Reminder", msg)
                                await user.send(embed=embed)
                            except Exception:
                                pass
                            items.remove(r)
                            changed = True
                    if not items:
                        self.reminders.pop(user_id, None)
                if changed:
                    self.save_reminders()
            await asyncio.sleep(5)

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

    # ==================== REMINDERS ====================
    @commands.hybrid_command(name="remindme", description="Set a reminder for yourself (e.g. 10m, 1h, 2d)")
    @app_commands.describe(duration="How long until the reminder (10m, 1h, 2d)", message="What to remind you about")
    async def remindme(self, ctx: commands.Context, duration: str, *, message: str = "Reminder!"):
        seconds = self._parse_duration(duration)
        if seconds is None:
            return await ctx.send(embed=self.get_embed("⚠️ Invalid Duration", "Use format like `10m`, `1h`, `2d`.", 0xFFAA00))
        ts = int(time.time()) + seconds
        rid = uuid.uuid4().hex[:8]
        user_id = str(ctx.author.id)
        if self.use_db:
            try:
                coll = self.bot.db["reminders"]
                await coll.insert_one({
                    "user_id": user_id,
                    "id": rid,
                    "timestamp": ts,
                    "message": message,
                    "created_at": int(time.time())
                })
            except Exception:
                return await ctx.send(embed=self.get_embed("❌ Error", "Failed to save reminder to database.", 0xFF0000))
        else:
            if user_id not in self.reminders:
                self.reminders[user_id] = []
            self.reminders[user_id].append({
                "id": rid,
                "timestamp": ts,
                "message": message,
                "created_at": int(time.time())
            })
            self.save_reminders()
        await ctx.send(embed=self.get_embed("✅ Reminder Set", f"I'll remind you in **{duration}** — ID: `{rid}`"))

    @commands.hybrid_command(name="reminders", description="List your active reminders")
    async def reminders_list(self, ctx: commands.Context):
        user_id = str(ctx.author.id)
        if self.use_db:
            try:
                coll = self.bot.db["reminders"]
                docs = await coll.find({"user_id": user_id}).to_list(length=None)
                items = docs
            except Exception:
                items = []
        else:
            items = self.reminders.get(user_id, [])
        if not items:
            return await ctx.send(embed=self.get_embed("⏳ Reminders", "You have no active reminders."))
        desc = ""
        for r in items:
            remain = r.get("timestamp") - int(time.time())
            if remain < 0:
                remain = 0
            m, s = divmod(remain, 60)
            h, m = divmod(m, 60)
            d, h = divmod(h, 24)
            timestr = f"{d}d {h}h {m}m {s}s"
            desc += f"• `{r['id']}` in **{timestr}** — {r.get('message')}\n"
        await ctx.send(embed=self.get_embed("⏳ Your Reminders", desc))

    @commands.hybrid_command(name="cancelreminder", description="Cancel a reminder by ID")
    async def cancelreminder(self, ctx: commands.Context, reminder_id: str):
        user_id = str(ctx.author.id)
        if self.use_db:
            try:
                coll = self.bot.db["reminders"]
                res = await coll.delete_one({"user_id": user_id, "id": reminder_id})
                if res.deleted_count:
                    return await ctx.send(embed=self.get_embed("✅ Cancelled", f"Cancelled reminder `{reminder_id}`."))
                else:
                    return await ctx.send(embed=self.get_embed("❌ Not Found", "No reminder found with that ID.", 0xFF0000))
            except Exception:
                return await ctx.send(embed=self.get_embed("❌ Error", "Failed to cancel reminder.", 0xFF0000))
        else:
            items = self.reminders.get(user_id, [])
            for r in list(items):
                if r.get("id") == reminder_id:
                    items.remove(r)
                    if not items:
                        self.reminders.pop(user_id, None)
                    self.save_reminders()
                    return await ctx.send(embed=self.get_embed("✅ Cancelled", f"Cancelled reminder `{reminder_id}`."))
            await ctx.send(embed=self.get_embed("❌ Not Found", "No reminder found with that ID.", 0xFF0000))

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
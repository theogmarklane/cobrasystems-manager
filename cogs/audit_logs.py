import asyncio
from datetime import datetime, timezone
import discord
from discord.ext import commands


class AuditLogs(commands.Cog):
    """Comprehensive server logging: messages, edits, deletes, moderation, channels, roles, threads, invites, voice, and guild changes."""

    def __init__(self, bot):
        self.bot = bot

    def get_embed(self, title: str, description: str = None, color=None):
        embed = discord.Embed(
            title=title,
            description=description,
            color=color or self.bot.embed_color,
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_footer(text=self.bot.footer)
        return embed

    def _truncate(self, text: str | None, limit: int = 1024) -> str:
        if not text:
            return "None"
        if len(text) <= limit:
            return text
        return text[: limit - 3] + "..."

    def _guild_log_channel(self, guild: discord.Guild):
        log_channels = self.bot.config.get("log_channel", {})
        channel_id = log_channels.get(str(guild.id))
        if not channel_id:
            return None
        return guild.get_channel(channel_id)

    async def _send_log(self, guild: discord.Guild, embed: discord.Embed):
        channel = self._guild_log_channel(guild)
        if not channel:
            return
        try:
            await channel.send(embed=embed, allowed_mentions=discord.AllowedMentions.none())
        except discord.Forbidden:
            pass
        except Exception:
            pass

    async def _audit_executor(self, guild: discord.Guild, action: discord.AuditLogAction, target_id: int | None):
        try:
            async for entry in guild.audit_logs(limit=6, action=action):
                if target_id is None:
                    return entry
                if entry.target and getattr(entry.target, "id", None) == target_id:
                    # keep it recent so we don't attribute old actions incorrectly
                    if (datetime.now(timezone.utc) - entry.created_at).total_seconds() <= 20:
                        return entry
        except Exception:
            return None
        return None

    def _author_text(self, user: discord.abc.User | None):
        if not user:
            return "Unknown"
        return f"{user.mention} (`{user.id}`)"

    def _role_list(self, before_roles, after_roles):
        before_ids = {r.id for r in before_roles}
        after_ids = {r.id for r in after_roles}
        added = [r for r in after_roles if r.id not in before_ids and not r.is_default()]
        removed = [r for r in before_roles if r.id not in after_ids and not r.is_default()]
        return added, removed

    async def _log_member_join(self, member: discord.Member):
        embed = self.get_embed(
            "👋 Member Joined",
            f"**User:** {self._author_text(member)}\n"
            f"**Account Created:** <t:{int(member.created_at.timestamp())}:F> • <t:{int(member.created_at.timestamp())}:R>\n"
            f"**Bot:** {'Yes' if member.bot else 'No'}"
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        if member.guild.icon:
            embed.set_author(name=member.guild.name, icon_url=member.guild.icon.url)
        await self._send_log(member.guild, embed)

    async def _log_member_remove(self, member: discord.Member):
        guild = member.guild
        kick_entry = await self._audit_executor(guild, discord.AuditLogAction.kick, member.id)
        if kick_entry:
            embed = self.get_embed(
                "👢 Member Kicked",
                f"**User:** {self._author_text(member)}\n"
                f"**Moderator:** {self._author_text(kick_entry.user)}\n"
                f"**Reason:** {kick_entry.reason or 'No reason provided'}"
            )
        else:
            embed = self.get_embed(
                "🚪 Member Left",
                f"**User:** {self._author_text(member)}\n"
                f"**Joined Server:** {f'<t:{int(member.joined_at.timestamp())}:F>' if member.joined_at else 'Unknown'}"
            )
        embed.set_thumbnail(url=member.display_avatar.url)
        await self._send_log(guild, embed)

    async def _log_member_ban(self, guild: discord.Guild, user: discord.User):
        entry = await self._audit_executor(guild, discord.AuditLogAction.ban, user.id)
        embed = self.get_embed(
            "🔨 Member Banned",
            f"**User:** {self._author_text(user)}\n"
            f"**Moderator:** {self._author_text(entry.user if entry else None)}\n"
            f"**Reason:** {entry.reason or 'No reason provided' if entry else 'No reason provided'}"
        )
        await self._send_log(guild, embed)

    async def _log_member_unban(self, guild: discord.Guild, user: discord.User):
        entry = await self._audit_executor(guild, discord.AuditLogAction.unban, user.id)
        embed = self.get_embed(
            "✅ Member Unbanned",
            f"**User:** {self._author_text(user)}\n"
            f"**Moderator:** {self._author_text(entry.user if entry else None)}\n"
            f"**Reason:** {entry.reason or 'No reason provided' if entry else 'No reason provided'}"
        )
        await self._send_log(guild, embed)

    async def _log_message_delete(self, message: discord.Message, *, raw: bool = False):
        if not message.guild:
            return
        content = getattr(message, "content", None)
        attachments = getattr(message, "attachments", []) or []
        embed = self.get_embed(
            "🗑️ Message Deleted",
            f"**Author:** {self._author_text(getattr(message, 'author', None))}\n"
            f"**Channel:** {getattr(message.channel, 'mention', f'<#{message.channel.id}>')}\n"
            f"**Message ID:** `{message.id}`\n"
            f"**Content:**\n```\n{self._truncate(content, 800)}\n```"
        )
        if attachments:
            embed.add_field(
                name="Attachments",
                value="\n".join(a.url for a in attachments[:5]),
                inline=False,
            )
        if raw:
            embed.set_footer(text=f"Raw delete event • {self.bot.footer}")
        await self._send_log(message.guild, embed)

    async def _log_message_edit(self, before: discord.Message, after: discord.Message, *, raw: bool = False):
        if not after.guild:
            return
        if before.content == after.content:
            return
        embed = self.get_embed(
            "✏️ Message Edited",
            f"**Author:** {self._author_text(after.author)}\n"
            f"**Channel:** {after.channel.mention}\n"
            f"**Message ID:** `{after.id}`"
        )
        embed.add_field(name="Before", value=f"```\n{self._truncate(before.content, 900)}\n```", inline=False)
        embed.add_field(name="After", value=f"```\n{self._truncate(after.content, 900)}\n```", inline=False)
        if raw:
            embed.set_footer(text=f"Raw edit event • {self.bot.footer}")
        await self._send_log(after.guild, embed)

    async def _log_bulk_delete(self, guild: discord.Guild, messages):
        messages = list(messages)
        if not messages:
            return
        desc_lines = []
        for msg in messages[:10]:
            author = getattr(msg, "author", None)
            content = self._truncate(getattr(msg, "content", None), 160)
            desc_lines.append(f"**{self._author_text(author)}** in <#{msg.channel.id}>: {content}")
        embed = self.get_embed(
            "🧹 Bulk Messages Deleted",
            f"**Count:** {len(messages)}\n\n" + "\n".join(desc_lines)
        )
        await self._send_log(guild, embed)

    async def _log_role_change(self, title: str, role: discord.Role, executor: discord.abc.User | None = None, reason: str | None = None):
        embed = self.get_embed(
            title,
            f"**Role:** {role.mention} (`{role.id}`)\n"
            f"**Moderator:** {self._author_text(executor)}\n"
            f"**Reason:** {reason or 'No reason provided'}"
        )
        embed.color = role.color if role.color.value else self.bot.embed_color
        await self._send_log(role.guild, embed)

    async def _log_channel_change(self, title: str, channel: discord.abc.GuildChannel, executor: discord.abc.User | None = None, reason: str | None = None):
        embed = self.get_embed(
            title,
            f"**Channel:** {channel.mention if hasattr(channel, 'mention') else f'<#{channel.id}>'} (`{channel.id}`)\n"
            f"**Moderator:** {self._author_text(executor)}\n"
            f"**Reason:** {reason or 'No reason provided'}"
        )
        await self._send_log(channel.guild, embed)

    async def _log_voice_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        changes = []
        if before.channel != after.channel:
            if before.channel and after.channel:
                changes.append(f"Moved: {before.channel.mention} → {after.channel.mention}")
            elif after.channel:
                changes.append(f"Joined: {after.channel.mention}")
            else:
                changes.append(f"Left voice: {before.channel.mention if before.channel else 'Unknown'}")
        toggles = [
            ("Server Mute", before.mute, after.mute),
            ("Server Deaf", before.deaf, after.deaf),
            ("Self Mute", before.self_mute, after.self_mute),
            ("Self Deaf", before.self_deaf, after.self_deaf),
            ("Streaming", before.self_stream, after.self_stream),
            ("Video", before.self_video, after.self_video),
        ]
        for label, b, a in toggles:
            if b != a:
                changes.append(f"{label}: {'Enabled' if a else 'Disabled'}")
        if not changes:
            return
        embed = self.get_embed(
            "🔊 Voice State Update",
            f"**Member:** {self._author_text(member)}\n" + "\n".join(f"• {c}" for c in changes)
        )
        await self._send_log(member.guild, embed)

    # ==================== MEMBER EVENTS ====================
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

        await self._log_member_join(member)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        await self._log_member_remove(member)

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        await self._log_member_ban(guild, user)

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User):
        await self._log_member_unban(guild, user)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.nick != after.nick:
            embed = self.get_embed(
                "📝 Nickname Changed",
                f"**Member:** {self._author_text(after)}\n**Before:** {before.nick or 'None'}\n**After:** {after.nick or 'None'}"
            )
            await self._send_log(after.guild, embed)

        added, removed = self._role_list(before.roles, after.roles)
        if added or removed:
            changes = []
            if added:
                changes.append("**Added:** " + ", ".join(r.mention for r in added))
            if removed:
                changes.append("**Removed:** " + ", ".join(r.mention for r in removed))
            executor = None
            reason = None
            try:
                entry = await self._audit_executor(after.guild, discord.AuditLogAction.member_role_update, after.id)
                if entry:
                    executor = entry.user
                    reason = entry.reason
            except Exception:
                pass
            embed = self.get_embed(
                "🎭 Member Roles Updated",
                f"**Member:** {self._author_text(after)}\n"
                f"**Moderator:** {self._author_text(executor)}\n"
                f"**Reason:** {reason or 'No reason provided'}\n\n" + "\n".join(changes)
            )
            await self._send_log(after.guild, embed)

        if before.timed_out_until != after.timed_out_until:
            embed = self.get_embed(
                "⏱️ Timeout Updated",
                f"**Member:** {self._author_text(after)}\n"
                f"**Before:** {before.timed_out_until or 'None'}\n"
                f"**After:** {after.timed_out_until or 'None'}"
            )
            await self._send_log(after.guild, embed)

    # ==================== MESSAGE EVENTS ====================
    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        await self._log_message_delete(message)

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent):
        guild = self.bot.get_guild(payload.guild_id) if payload.guild_id else None
        if not guild:
            return
        cached = payload.cached_message
        if cached:
            await self._log_message_delete(cached, raw=True)
            return
        channel = guild.get_channel(payload.channel_id)
        if not channel:
            return
        embed = self.get_embed(
            "🗑️ Message Deleted",
            f"**Channel:** <#{payload.channel_id}>\n**Message ID:** `{payload.message_id}`\n**Content:** Unknown (message not cached)"
        )
        embed.set_footer(text=f"Raw delete event • {self.bot.footer}")
        await self._send_log(guild, embed)

    @commands.Cog.listener()
    async def on_bulk_message_delete(self, messages):
        if not messages:
            return
        guild = messages[0].guild if messages and hasattr(messages[0], "guild") else None
        if guild:
            await self._log_bulk_delete(guild, messages)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        await self._log_message_edit(before, after)

    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload: discord.RawMessageUpdateEvent):
        guild = self.bot.get_guild(payload.guild_id) if payload.guild_id else None
        if not guild:
            return
        cached = payload.cached_message
        if cached:
            before = cached
            after = cached
            data = payload.data
            # Build a lightweight after-message-like object using cached content where possible
            content = data.get("content", cached.content)
            if content == cached.content:
                return
            embed = self.get_embed(
                "✏️ Message Edited",
                f"**Author:** {self._author_text(cached.author)}\n**Channel:** <#{cached.channel.id}>\n**Message ID:** `{cached.id}`"
            )
            embed.add_field(name="Before", value=f"```\n{self._truncate(cached.content, 900)}\n```", inline=False)
            embed.add_field(name="After", value=f"```\n{self._truncate(content, 900)}\n```", inline=False)
            embed.set_footer(text=f"Raw edit event • {self.bot.footer}")
            await self._send_log(guild, embed)
            return

    # ==================== REACTIONS ====================
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id:
            return
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return
        channel = guild.get_channel(payload.channel_id)
        if not channel:
            return
        embed = self.get_embed(
            "➕ Reaction Added",
            f"**User ID:** `{payload.user_id}`\n**Channel:** <#{payload.channel_id}>\n**Message ID:** `{payload.message_id}`\n**Reaction:** {payload.emoji}"
        )
        await self._send_log(guild, embed)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id:
            return
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return
        embed = self.get_embed(
            "➖ Reaction Removed",
            f"**User ID:** `{payload.user_id}`\n**Channel:** <#{payload.channel_id}>\n**Message ID:** `{payload.message_id}`\n**Reaction:** {payload.emoji}"
        )
        await self._send_log(guild, embed)

    @commands.Cog.listener()
    async def on_raw_reaction_clear(self, payload: discord.RawReactionClearEvent):
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return
        embed = self.get_embed(
            "🧽 Reactions Cleared",
            f"**Channel:** <#{payload.channel_id}>\n**Message ID:** `{payload.message_id}`"
        )
        await self._send_log(guild, embed)

    @commands.Cog.listener()
    async def on_raw_reaction_clear_emoji(self, payload: discord.RawReactionClearEmojiEvent):
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return
        embed = self.get_embed(
            "🧼 Emoji Reactions Cleared",
            f"**Channel:** <#{payload.channel_id}>\n**Message ID:** `{payload.message_id}`\n**Emoji:** {payload.emoji}"
        )
        await self._send_log(guild, embed)

    # ==================== CHANNELS ====================
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        embed = self.get_embed(
            "📁 Channel Created",
            f"**Channel:** {channel.mention if hasattr(channel, 'mention') else f'<#{channel.id}>'} (`{channel.id}`)\n**Type:** {channel.type}"
        )
        await self._send_log(channel.guild, embed)

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel):
        changes = []
        if before.name != after.name:
            changes.append(f"**Name:** {before.name} → {after.name}")
        if getattr(before, "topic", None) != getattr(after, "topic", None):
            changes.append("**Topic** changed")
        if getattr(before, "overwrites", None) != getattr(after, "overwrites", None):
            changes.append("**Permissions** changed")
        if not changes:
            return
        embed = self.get_embed(
            "🛠️ Channel Updated",
            f"**Channel:** {after.mention if hasattr(after, 'mention') else f'<#{after.id}>'} (`{after.id}`)\n" + "\n".join(changes)
        )
        await self._send_log(after.guild, embed)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        embed = self.get_embed(
            "🗑️ Channel Deleted",
            f"**Channel:** {getattr(channel, 'mention', f'<#{channel.id}>')} (`{channel.id}`)\n**Type:** {channel.type}"
        )
        await self._send_log(channel.guild, embed)

    # ==================== ROLES ====================
    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role):
        await self._log_role_change("🎭 Role Created", role)

    @commands.Cog.listener()
    async def on_guild_role_update(self, before: discord.Role, after: discord.Role):
        changes = []
        if before.name != after.name:
            changes.append(f"**Name:** {before.name} → {after.name}")
        if before.colour != after.colour:
            changes.append(f"**Color:** {before.colour} → {after.colour}")
        if before.hoist != after.hoist:
            changes.append(f"**Hoist:** {before.hoist} → {after.hoist}")
        if before.mentionable != after.mentionable:
            changes.append(f"**Mentionable:** {before.mentionable} → {after.mentionable}")
        if before.permissions != after.permissions:
            changes.append("**Permissions** changed")
        if not changes:
            return
        entry = await self._audit_executor(after.guild, discord.AuditLogAction.role_update, after.id)
        embed = self.get_embed(
            "🛠️ Role Updated",
            f"**Role:** {after.mention} (`{after.id}`)\n"
            f"**Moderator:** {self._author_text(entry.user if entry else None)}\n"
            f"**Reason:** {entry.reason or 'No reason provided' if entry else 'No reason provided'}\n\n" + "\n".join(changes)
        )
        embed.color = after.color if after.color.value else self.bot.embed_color
        await self._send_log(after.guild, embed)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        entry = await self._audit_executor(role.guild, discord.AuditLogAction.role_delete, role.id)
        embed = self.get_embed(
            "🗑️ Role Deleted",
            f"**Role:** {role.name} (`{role.id}`)\n"
            f"**Moderator:** {self._author_text(entry.user if entry else None)}\n"
            f"**Reason:** {entry.reason or 'No reason provided' if entry else 'No reason provided'}"
        )
        embed.color = role.color if role.color.value else self.bot.embed_color
        await self._send_log(role.guild, embed)

    # ==================== THREADS ====================
    @commands.Cog.listener()
    async def on_thread_create(self, thread: discord.Thread):
        embed = self.get_embed(
            "🧵 Thread Created",
            f"**Thread:** {thread.mention} (`{thread.id}`)\n**Parent:** <#{thread.parent_id}>"
        )
        await self._send_log(thread.guild, embed)

    @commands.Cog.listener()
    async def on_thread_update(self, before: discord.Thread, after: discord.Thread):
        changes = []
        if before.name != after.name:
            changes.append(f"**Name:** {before.name} → {after.name}")
        if before.archived != after.archived:
            changes.append(f"**Archived:** {before.archived} → {after.archived}")
        if before.locked != after.locked:
            changes.append(f"**Locked:** {before.locked} → {after.locked}")
        if not changes:
            return
        embed = self.get_embed(
            "🧵 Thread Updated",
            f"**Thread:** {after.mention} (`{after.id}`)\n" + "\n".join(changes)
        )
        await self._send_log(after.guild, embed)

    @commands.Cog.listener()
    async def on_thread_delete(self, thread: discord.Thread):
        embed = self.get_embed(
            "🗑️ Thread Deleted",
            f"**Thread:** {thread.name} (`{thread.id}`)\n**Parent:** <#{thread.parent_id}>"
        )
        await self._send_log(thread.guild, embed)

    @commands.Cog.listener()
    async def on_thread_member_join(self, member: discord.ThreadMember):
        pass

    @commands.Cog.listener()
    async def on_thread_member_remove(self, member: discord.ThreadMember):
        pass

    # ==================== VOICE ====================
    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        await self._log_voice_update(member, before, after)

    # ==================== INVITES / EMOJIS / GUILD ====================
    @commands.Cog.listener()
    async def on_invite_create(self, invite: discord.Invite):
        embed = self.get_embed(
            "🔗 Invite Created",
            f"**Code:** `{invite.code}`\n**Channel:** {invite.channel.mention if invite.channel else 'Unknown'}\n"
            f"**Created By:** {self._author_text(invite.inviter)}\n**Max Uses:** {invite.max_uses or 'Unlimited'}\n**Expires:** {invite.max_age or 'Never'}"
        )
        await self._send_log(invite.guild, embed)

    @commands.Cog.listener()
    async def on_invite_delete(self, invite: discord.Invite):
        embed = self.get_embed(
            "🗑️ Invite Deleted",
            f"**Code:** `{invite.code}`\n**Channel:** {invite.channel.mention if invite.channel else 'Unknown'}"
        )
        await self._send_log(invite.guild, embed)

    @commands.Cog.listener()
    async def on_guild_emojis_update(self, guild: discord.Guild, before, after):
        before_ids = {e.id for e in before}
        after_ids = {e.id for e in after}
        added = [e for e in after if e.id not in before_ids]
        removed = [e for e in before if e.id not in after_ids]
        if not added and not removed:
            return
        desc = []
        if added:
            desc.append("**Added:** " + ", ".join(str(e) for e in added))
        if removed:
            desc.append("**Removed:** " + ", ".join(str(e) for e in removed))
        embed = self.get_embed("😀 Emojis Updated", "\n".join(desc))
        await self._send_log(guild, embed)

    @commands.Cog.listener()
    async def on_guild_update(self, before: discord.Guild, after: discord.Guild):
        changes = []
        if before.name != after.name:
            changes.append(f"**Name:** {before.name} → {after.name}")
        if before.icon != after.icon:
            changes.append("**Icon** changed")
        if before.banner != after.banner:
            changes.append("**Banner** changed")
        if before.verification_level != after.verification_level:
            changes.append(f"**Verification:** {before.verification_level} → {after.verification_level}")
        if not changes:
            return
        embed = self.get_embed("🏠 Guild Updated", "\n".join(changes))
        await self._send_log(after, embed)

    # ==================== RAW CHANNEL / ROLE / MEMBER AUDIT HELPERS ====================
    @commands.Cog.listener()
    async def on_webhooks_update(self, channel: discord.abc.GuildChannel):
        embed = self.get_embed(
            "🪝 Webhooks Updated",
            f"**Channel:** {channel.mention if hasattr(channel, 'mention') else f'<#{channel.id}>'} (`{channel.id}`)"
        )
        await self._send_log(channel.guild, embed)


async def setup(bot):
    await bot.add_cog(AuditLogs(bot))

import aiohttp
import asyncio
import discord
from discord.ext import commands
import xml.etree.ElementTree as ET
import re


class YTNotifications(commands.Cog):
    """Poll YouTube channel feeds and post new uploads to configured discord channels."""

    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        self.task = bot.loop.create_task(self.loop_poll())

    def cog_unload(self):
        try:
            self.task.cancel()
        except Exception:
            pass
        try:
            asyncio.create_task(self.session.close())
        except Exception:
            pass

    async def loop_poll(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try:
                await self.check_feeds()
            except Exception:
                pass
            await asyncio.sleep(self.bot.config.get("yt_poll_interval", 60))

    async def check_feeds(self):
        subs = self.bot.config.get("youtube_subscriptions", [])
        # subs: list of dicts {"channel_id": "UCxxx", "guild_id": "123", "notify_channel": 456}
        for sub in list(subs):
            channel_id = sub.get("channel_id")
            guild_id = int(sub.get("guild_id"))
            notify_channel_id = int(sub.get("notify_channel"))
            feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
            try:
                async with self.session.get(feed_url, timeout=20) as resp:
                    if resp.status != 200:
                        continue
                    text = await resp.text()
                    root = ET.fromstring(text)
                    # namespace handling
                    ns = {k: v for k, v in [part.split('=') for part in [n for n in root.tag[root.tag.find('{')+1:root.tag.find('}')].split()]]} if False else {}
                    # simple parse: find first entry
                    entry = root.find('{http://www.w3.org/2005/Atom}entry')
                    if entry is None:
                        continue
                    video_id = entry.find('{http://www.youtube.com/xml/schemas/2015}videoId')
                    title = entry.find('{http://www.w3.org/2005/Atom}title')
                    link = entry.find('{http://www.w3.org/2005/Atom}link')
                    media_thumbnail = entry.find('{http://search.yahoo.com/mrss/}group/{http://search.yahoo.com/mrss/}thumbnail')
                    if video_id is None or title is None:
                        continue
                    vid = video_id.text
                    last_seen = self.bot.config.setdefault("yt_last", {}).get(channel_id)
                    if last_seen == vid:
                        continue
                    # new video
                    self.bot.config.setdefault("yt_last", {})[channel_id] = vid
                    self.bot.save_config()
                    guild = self.bot.get_guild(guild_id)
                    if not guild:
                        continue
                    channel = guild.get_channel(notify_channel_id)
                    if not channel:
                        continue
                    video_url = f"https://www.youtube.com/watch?v={vid}"
                    embed = discord.Embed(title=title.text, url=video_url, color=self.bot.embed_color)
                    if media_thumbnail is not None and 'url' in media_thumbnail.attrib:
                        embed.set_thumbnail(url=media_thumbnail.attrib['url'])
                    embed.set_footer(text="New YouTube upload")
                    try:
                        await channel.send(embed=embed)
                    except Exception:
                        pass
            except Exception:
                continue

    @commands.command(name="ytsub")
    @commands.has_permissions(manage_guild=True)
    async def ytsub(self, ctx, channel_identifier: str, notify_channel: discord.TextChannel = None):
        """Subscribe this server to a YouTube channel's uploads. channel_identifier may be a channel ID or full channel URL.
        Example: /ytsub UC_xxx #youtube"""
        cid = channel_identifier.strip()

        # If a full URL/handle/custom name was provided, try to resolve it to a UC channel id
        if not cid.startswith("UC"):
            # handle common URL forms and plain handles
            # Examples: https://www.youtube.com/@RinOmega, https://www.youtube.com/channel/UC..., https://youtube.com/c/Name
            if "youtube.com" in cid or "youtu.be" in cid or cid.startswith("@"):
                # normalize if just a handle like @RinOmega
                if cid.startswith("@"):
                    test_url = f"https://www.youtube.com/{cid}"
                else:
                    test_url = cid

                try:
                    async with self.session.get(test_url, timeout=20) as resp:
                        if resp.status == 200:
                            text = await resp.text()
                            # Try to find channelId in page HTML or JSON
                            m = re.search(r'"channelId"\s*:\s*"(UC[0-9A-Za-z_-]{20,})"', text)
                            if not m:
                                m = re.search(r'"externalId"\s*:\s*"(UC[0-9A-Za-z_-]{20,})"', text)
                            if not m:
                                # sometimes the HTML contains /channel/UC... as a canonical link
                                m = re.search(r"/channel/(UC[0-9A-Za-z_-]{20,})", text)
                            if m:
                                cid = m.group(1)
                except Exception:
                    pass

        if not cid.startswith("UC"):
            await ctx.send("Please provide a channel ID (starts with UC) or a full channel URL/handle that can be resolved.")
            return

        notify_channel = notify_channel or ctx.channel
        subs = self.bot.config.setdefault("youtube_subscriptions", [])
        subs.append({"channel_id": cid, "guild_id": str(ctx.guild.id), "notify_channel": notify_channel.id})
        self.bot.save_config()
        await ctx.send(f"Subscribed to uploads from `{cid}` and will notify in {notify_channel.mention}.")

    @commands.command(name="ytunsub")
    @commands.has_permissions(manage_guild=True)
    async def ytunsub(self, ctx, channel_id: str):
        subs = self.bot.config.setdefault("youtube_subscriptions", [])
        before = len(subs)
        subs = [s for s in subs if not (s.get("channel_id") == channel_id and s.get("guild_id") == str(ctx.guild.id))]
        self.bot.config["youtube_subscriptions"] = subs
        self.bot.save_config()
        await ctx.send(f"Unsubscribed `{channel_id}` for this server.")


async def setup(bot):
    await bot.add_cog(YTNotifications(bot))

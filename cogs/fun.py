import discord
from discord.ext import commands
from discord import app_commands
import random
from datetime import datetime

class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.jokes = [
            "I told my computer I needed a break, and it said 'No problem — I'll go to sleep.'",
            "Why do programmers prefer dark mode? Because light attracts bugs.",
            "There are only 10 types of people in the world: those who understand binary, and those who don't."
        ]

    def get_embed(self, title: str, description: str = None, color=None):
        embed = discord.Embed(
            title=title,
            description=description,
            color=color or self.bot.embed_color,
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text=self.bot.footer)
        return embed

    @commands.hybrid_command(name="coin", description="Flip a coin")
    async def coin(self, ctx: commands.Context):
        res = random.choice(["Heads", "Tails"])
        await ctx.send(embed=self.get_embed("🪙 Coin Flip", f"Result: **{res}**"))

    @commands.hybrid_command(name="roll", description="Roll dice (e.g. 2d6, d20)")
    @app_commands.describe(sides="Dice expression like 2d6 or d20")
    async def roll(self, ctx: commands.Context, sides: str = "1d6"):
        try:
            if 'd' not in sides:
                return await ctx.send(embed=self.get_embed("⚠️ Invalid", "Use format like `2d6` or `d20`.", 0xFFAA00))
            parts = sides.lower().split('d')
            count = int(parts[0]) if parts[0] else 1
            die = int(parts[1])
            if count < 1 or count > 100 or die < 2 or die > 10000:
                return await ctx.send(embed=self.get_embed("⚠️ Invalid", "Dice out of allowed range.", 0xFFAA00))
            rolls = [random.randint(1, die) for _ in range(count)]
            total = sum(rolls)
            await ctx.send(embed=self.get_embed("🎲 Roll", f"Rolls: {rolls}\nTotal: **{total}**"))
        except Exception as e:
            await ctx.send(embed=self.get_embed("❌ Error", str(e), 0xFF0000))

    @commands.hybrid_command(name="choose", description="Choose between multiple options")
    async def choose(self, ctx: commands.Context, *, options: str):
        opts = [o.strip() for o in options.split(",") if o.strip()]
        if len(opts) < 2:
            return await ctx.send(embed=self.get_embed("⚠️ Invalid", "Provide at least two comma-separated options.", 0xFFAA00))
        pick = random.choice(opts)
        await ctx.send(embed=self.get_embed("🎯 Choice", f"I pick: **{pick}**"))

    @commands.hybrid_command(name="joke", description="Tell a silly joke")
    async def joke(self, ctx: commands.Context):
        await ctx.send(embed=self.get_embed("😂 Joke", random.choice(self.jokes)))

    @commands.hybrid_command(name="rps", description="Play rock-paper-scissors")
    async def rps(self, ctx: commands.Context, choice: str):
        choice = choice.lower()
        if choice not in ("rock", "paper", "scissors"):
            return await ctx.send(embed=self.get_embed("⚠️ Invalid", "Choose rock, paper, or scissors.", 0xFFAA00))
        bot_choice = random.choice(["rock", "paper", "scissors"])
        if choice == bot_choice:
            result = "Tie"
        elif (choice == "rock" and bot_choice == "scissors") or (choice == "paper" and bot_choice == "rock") or (choice == "scissors" and bot_choice == "paper"):
            result = "You Win"
        else:
            result = "You Lose"
        await ctx.send(embed=self.get_embed("✊ Rock Paper Scissors", f"You: **{choice}**\nBot: **{bot_choice}**\nResult: **{result}**"))

async def setup(bot):
    await bot.add_cog(Fun(bot))

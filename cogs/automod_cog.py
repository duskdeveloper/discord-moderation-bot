import discord
from discord.ext import commands
from utils.automod import AutoMod
import json

class AutoModCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        with open('config.json', 'r') as f:
            config = json.load(f)
        self.automod = AutoMod(bot, config)
        
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return
            
        violation = await self.automod.check_message(message)
        if violation:
            await self.automod.handle_violation(message, violation)
            
    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if hasattr(self.bot, 'logger'):
            await self.bot.logger.log_message_delete(message)

async def setup(bot):
    await bot.add_cog(AutoModCog(bot))

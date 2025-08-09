import logging
import json
import discord
from datetime import datetime
from typing import Dict, Any

def setup_logging() -> logging.Logger:
    with open('config.json', 'r') as f:
        config = json.load(f)
    
    log_config = config.get('logging', {})
    
    logging.basicConfig(
        level=getattr(logging, log_config.get('level', 'INFO')),
        format=log_config.get('format', '[%(asctime)s] [%(levelname)s] %(name)s: %(message)s'),
        handlers=[
            logging.FileHandler(log_config.get('file', 'bot.log')),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger('ModerationBot')

class ModerationLogger:
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
        
    async def log_action(self, guild_id: int, action_data: Dict[str, Any]):
        guild_config = await self.bot.db.get_guild_config(guild_id)
        log_channel_id = guild_config.get('log_channel')
        
        if not log_channel_id:
            return
            
        channel = self.bot.get_channel(log_channel_id)
        if not channel:
            return
            
        embed = self._create_log_embed(action_data)
        
        try:
            await channel.send(embed=embed)
        except Exception as e:
            self.logger.error(f"Failed to send log message: {e}")
            
    def _create_log_embed(self, data: Dict[str, Any]):
        action = data.get('action', 'Unknown')
        user_id = data.get('user_id')
        moderator_id = data.get('moderator_id')
        reason = data.get('reason', 'No reason provided')
        duration = data.get('duration')
        
        color_map = {
            'warn': 0xff9900,
            'timeout': 0xff6600,
            'ban': 0xff0000,
            'kick': 0xff3300,
            'unban': 0x00ff00,
            'unwarn': 0x0099ff,
            'purge': 0x9900ff
        }
        
        embed = discord.Embed(
            title=f"🔨 Moderation Action: {action.title()}",
            color=color_map.get(action, 0x808080),
            timestamp=discord.utils.utcnow()
        )
        
        if user_id:
            user = self.bot.get_user(user_id)
            embed.add_field(
                name="User",
                value=f"{user.mention if user else f'<@{user_id}>'}\n`{user_id}`",
                inline=True
            )
            
        if moderator_id:
            moderator = self.bot.get_user(moderator_id)
            embed.add_field(
                name="Moderator",
                value=f"{moderator.mention if moderator else f'<@{moderator_id}>'}\n`{moderator_id}`",
                inline=True
            )
            
        embed.add_field(name="Reason", value=reason, inline=False)
        
        if duration:
            embed.add_field(name="Duration", value=f"{duration} seconds", inline=True)
            
        if data.get('warning_count'):
            embed.add_field(name="Total Warnings", value=str(data['warning_count']), inline=True)
            
        return embed
        
    async def log_message_delete(self, message):
        if message.author.bot:
            return
            
        guild_config = await self.bot.db.get_guild_config(message.guild.id)
        log_channel_id = guild_config.get('log_channel')
        
        if not log_channel_id:
            return
            
        channel = self.bot.get_channel(log_channel_id)
        if not channel or channel.id == message.channel.id:
            return
            
        embed = discord.Embed(
            title="🗑️ Message Deleted",
            color=0xff6600,
            timestamp=discord.utils.utcnow()
        )
        
        embed.add_field(
            name="User",
            value=f"{message.author.mention}\n`{message.author.id}`",
            inline=True
        )
        
        embed.add_field(
            name="Channel",
            value=f"{message.channel.mention}\n`{message.channel.id}`",
            inline=True
        )
        
        if message.content:
            content = message.content[:1000] + "..." if len(message.content) > 1000 else message.content
            embed.add_field(name="Content", value=f"```{content}```", inline=False)
            
        if message.attachments:
            attachment_list = "\n".join([f"[{att.filename}]({att.url})" for att in message.attachments])
            embed.add_field(name="Attachments", value=attachment_list, inline=False)
            
        try:
            await channel.send(embed=embed)
        except Exception as e:
            self.logger.error(f"Failed to log message deletion: {e}")

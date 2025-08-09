import re
import discord
from typing import List, Dict, Any, Optional
import asyncio
from datetime import datetime, timedelta

class AutoMod:
    def __init__(self, bot, config: Dict[str, Any]):
        self.bot = bot
        self.config = config
        self.spam_thresholds = config.get('spam_thresholds', {})
        self.blacklist_words = [word.lower() for word in config.get('blacklist_words', [])]
        
    async def check_message(self, message: discord.Message) -> Optional[str]:
        if message.author.bot:
            return None
            
        if not isinstance(message.author, discord.Member):
            return None
            
        if await self._is_immune(message.author):
            return None
            
        if not message.guild:
            return None
            
        guild_config = await self.bot.db.get_guild_config(message.guild.id)
        if not guild_config.get('automod_enabled', True):
            return None
            
        violation = None
        
        if guild_config.get('profanity_filter', True):
            violation = await self._check_profanity(message)
            if violation:
                return violation
                
        if guild_config.get('spam_detection', True):
            violation = await self._check_spam(message)
            if violation:
                return violation
                
        violation = await self._check_excessive_mentions(message)
        if violation:
            return violation
            
        violation = await self._check_excessive_emojis(message)
        if violation:
            return violation
            
        violation = await self._check_zalgo_text(message)
        if violation:
            return violation
            
        return None
        
    async def _is_immune(self, member: discord.Member) -> bool:
        if member.guild_permissions.administrator:
            return True
            
        immune_roles = self.config.get('immune_roles', [])
        for role in member.roles:
            if role.name in immune_roles:
                return True
                
        return False
        
    async def _check_profanity(self, message: discord.Message) -> Optional[str]:
        content_lower = message.content.lower()
        
        for word in self.blacklist_words:
            if word in content_lower:
                return f"Profanity detected: {word}"
                
        return None
        
    async def _check_spam(self, message: discord.Message) -> Optional[str]:
        if not message.guild:
            return None
            
        await self.bot.db.update_spam_tracking(
            message.guild.id, 
            message.author.id, 
            message.content
        )
        
        stats = await self.bot.db.get_spam_stats(message.guild.id, message.author.id)
        
        max_messages = self.spam_thresholds.get('messages_per_minute', 10)
        if stats['message_count'] > max_messages:
            return f"Spam detected: {stats['message_count']} messages in 1 minute"
            
        max_duplicates = self.spam_thresholds.get('duplicate_messages', 3)
        if stats['duplicate_count'] >= max_duplicates:
            return f"Duplicate message spam: {stats['duplicate_count']} identical messages"
            
        return None
        
    async def _check_excessive_mentions(self, message: discord.Message) -> Optional[str]:
        mention_limit = self.spam_thresholds.get('mention_limit', 5)
        mention_count = len(message.mentions) + len(message.role_mentions)
        
        if mention_count > mention_limit:
            return f"Excessive mentions: {mention_count} mentions (limit: {mention_limit})"
            
        return None
        
    async def _check_excessive_emojis(self, message: discord.Message) -> Optional[str]:
        emoji_limit = self.spam_thresholds.get('emoji_limit', 10)
        
        custom_emoji_pattern = r'<a?:[a-zA-Z0-9_]+:[0-9]+>'
        unicode_emoji_pattern = r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F700-\U0001F77F\U0001F780-\U0001F7FF\U0001F800-\U0001F8FF\U0001F900-\U0001F9FF\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF\U00002600-\U000026FF\U00002700-\U000027BF]'
        
        custom_emojis = len(re.findall(custom_emoji_pattern, message.content))
        unicode_emojis = len(re.findall(unicode_emoji_pattern, message.content))
        
        total_emojis = custom_emojis + unicode_emojis
        
        if total_emojis > emoji_limit:
            return f"Excessive emojis: {total_emojis} emojis (limit: {emoji_limit})"
            
        return None
        
    async def _check_zalgo_text(self, message: discord.Message) -> Optional[str]:
        zalgo_pattern = r'[\u0300-\u036f\u1ab0-\u1aff\u1dc0-\u1dff\u20d0-\u20ff\ufe20-\ufe2f]'
        zalgo_count = len(re.findall(zalgo_pattern, message.content))
        
        if zalgo_count > 10:
            return "Zalgo text detected"
            
        return None
        
    async def handle_violation(self, message: discord.Message, violation: str):
        if not message.guild or not isinstance(message.author, discord.Member):
            return
            
        try:
            await message.delete()
        except discord.NotFound:
            pass
        except discord.Forbidden:
            pass
            
        if not self.bot.user:
            return
            
        await self.bot.db.add_warning(
            message.guild.id,
            message.author.id,
            self.bot.user.id,
            f"Auto-moderation: {violation}"
        )
        
        warnings = await self.bot.db.get_user_warnings(message.guild.id, message.author.id)
        warning_count = len(warnings)
        
        guild_config = await self.bot.db.get_guild_config(message.guild.id)
        max_warnings = guild_config.get('max_warnings', 3)
        warning_actions = guild_config.get('warning_actions', {})
        
        embed = discord.Embed(
            title="⚠️ Auto-Moderation Alert",
            description=f"{message.author.mention}, your message was removed.",
            color=0xff9900,
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="Reason", value=violation, inline=False)
        embed.add_field(name="Warnings", value=f"{warning_count}/{max_warnings}", inline=True)
        
        if warning_count in warning_actions:
            action = warning_actions[str(warning_count)]
            
            if action == "timeout":
                timeout_duration = guild_config.get('timeout_duration', 300)
                try:
                    await message.author.timeout(
                        discord.utils.utcnow() + timedelta(seconds=timeout_duration),
                        reason=f"Auto-mod: {warning_count} warnings"
                    )
                    embed.add_field(
                        name="Action Taken", 
                        value=f"User timed out for {timeout_duration} seconds", 
                        inline=False
                    )
                except discord.Forbidden:
                    embed.add_field(
                        name="Action Failed", 
                        value="Could not timeout user (missing permissions)", 
                        inline=False
                    )
                    
            elif action == "ban":
                try:
                    await message.author.ban(
                        reason=f"Auto-mod: {warning_count} warnings",
                        delete_message_days=1
                    )
                    embed.add_field(
                        name="Action Taken", 
                        value="User has been banned", 
                        inline=False
                    )
                except discord.Forbidden:
                    embed.add_field(
                        name="Action Failed", 
                        value="Could not ban user (missing permissions)", 
                        inline=False
                    )
                    
        try:
            await message.channel.send(embed=embed, delete_after=10)
        except discord.Forbidden:
            pass
            
        await self.bot.db.log_moderation_action(
            message.guild.id,
            message.author.id,
            self.bot.user.id,
            "auto_warn",
            violation
        )

import discord
from discord.ext import commands
from typing import Optional, List
import asyncio
from datetime import datetime, timedelta

class ModerationCommands:
    """
    Additional moderation utilities and helper functions
    that complement the main ModerationCog
    """
    
    def __init__(self, bot):
        self.bot = bot
        
    async def get_user_info(self, guild: discord.Guild, user_id: int) -> Optional[dict]:
        """Get comprehensive user information for moderation purposes"""
        try:
            member = guild.get_member(user_id)
            if not member:
                try:
                    user = await self.bot.fetch_user(user_id)
                    return {
                        'user': user,
                        'member': None,
                        'in_guild': False,
                        'account_age': (datetime.utcnow() - user.created_at).days,
                        'avatar_url': user.display_avatar.url
                    }
                except discord.NotFound:
                    return None
            
            warnings = await self.bot.db.get_user_warnings(guild.id, user_id)
            
            return {
                'user': member,
                'member': member,
                'in_guild': True,
                'account_age': (datetime.utcnow() - member.created_at).days,
                'join_date': member.joined_at,
                'guild_age': (datetime.utcnow() - member.joined_at).days if member.joined_at else 0,
                'roles': [role.name for role in member.roles if role.name != '@everyone'],
                'top_role': member.top_role.name,
                'permissions': member.guild_permissions,
                'warning_count': len(warnings),
                'recent_warnings': warnings[:5],
                'avatar_url': member.display_avatar.url,
                'is_timed_out': member.is_timed_out(),
                'timeout_until': member.timed_out_until if member.is_timed_out() else None
            }
        except Exception as e:
            self.bot.logger.error(f"Error getting user info: {e}")
            return None
            
    async def create_moderation_embed(self, action: str, target: discord.User, 
                                    moderator: discord.User, reason: str, 
                                    **kwargs) -> discord.Embed:
        """Create standardized moderation embeds"""
        color_map = {
            'warn': 0xff9900,
            'timeout': 0xff6600,
            'kick': 0xff3300,
            'ban': 0xff0000,
            'unban': 0x00ff00,
            'unwarn': 0x0099ff,
            'purge': 0x9900ff,
            'info': 0x0099ff
        }
        
        embed = discord.Embed(
            title=f"🔨 {action.title()} Action",
            color=color_map.get(action.lower(), 0x808080),
            timestamp=discord.utils.utcnow()
        )
        
        embed.add_field(
            name="Target",
            value=f"{target.mention}\n`{target.id}`",
            inline=True
        )
        
        embed.add_field(
            name="Moderator",
            value=f"{moderator.mention}\n`{moderator.id}`",
            inline=True
        )
        
        if reason:
            embed.add_field(name="Reason", value=reason, inline=False)
            
        for key, value in kwargs.items():
            if value is not None:
                embed.add_field(name=key.replace('_', ' ').title(), value=str(value), inline=True)
                
        embed.set_thumbnail(url=target.display_avatar.url)
        
        return embed
        
    async def check_moderation_hierarchy(self, moderator: discord.Member, 
                                       target: discord.Member) -> tuple[bool, str]:
        """Check if moderator can perform actions on target"""
        if moderator.id == target.id:
            return False, "You cannot moderate yourself"
            
        if target.id == moderator.guild.owner_id:
            return False, "You cannot moderate the server owner"
            
        if moderator.id != moderator.guild.owner_id:
            if target.top_role >= moderator.top_role:
                return False, "You cannot moderate someone with equal or higher role"
                
        bot_member = moderator.guild.me
        if target.top_role >= bot_member.top_role:
            return False, "I cannot moderate someone with equal or higher role than me"
            
        return True, ""
        
    async def get_ban_list(self, guild: discord.Guild, limit: int = 100) -> List[dict]:
        """Get formatted ban list for the guild"""
        try:
            bans = []
            async for ban_entry in guild.bans(limit=limit):
                bans.append({
                    'user': ban_entry.user,
                    'reason': ban_entry.reason or 'No reason provided',
                    'user_id': ban_entry.user.id,
                    'username': f"{ban_entry.user.name}#{ban_entry.user.discriminator}"
                })
            return bans
        except discord.Forbidden:
            return []
            
    async def search_user(self, guild: discord.Guild, query: str) -> List[discord.Member]:
        """Search for users by name, nickname, or ID"""
        results = []
        query_lower = query.lower()
        
        # Try to find by ID first
        try:
            user_id = int(query)
            member = guild.get_member(user_id)
            if member:
                return [member]
        except ValueError:
            pass
            
        # Search by name and nickname
        for member in guild.members:
            if (query_lower in member.name.lower() or 
                query_lower in member.display_name.lower() or
                (member.nick and query_lower in member.nick.lower())):
                results.append(member)
                
        return results[:10]  # Limit to 10 results
        
    async def format_duration(self, seconds: int) -> str:
        """Format duration in human-readable format"""
        if seconds < 60:
            return f"{seconds} seconds"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"{minutes} minutes"
        elif seconds < 86400:
            hours = seconds // 3600
            return f"{hours} hours"
        else:
            days = seconds // 86400
            return f"{days} days"
            
    async def parse_duration(self, duration_str: str) -> Optional[int]:
        """Parse duration string to seconds"""
        duration_str = duration_str.lower().strip()
        
        multipliers = {
            's': 1, 'sec': 1, 'second': 1, 'seconds': 1,
            'm': 60, 'min': 60, 'minute': 60, 'minutes': 60,
            'h': 3600, 'hr': 3600, 'hour': 3600, 'hours': 3600,
            'd': 86400, 'day': 86400, 'days': 86400,
            'w': 604800, 'week': 604800, 'weeks': 604800
        }
        
        try:
            # Try parsing as just a number (assume seconds)
            return int(duration_str)
        except ValueError:
            pass
            
        # Try parsing with unit
        for unit, multiplier in multipliers.items():
            if duration_str.endswith(unit):
                try:
                    number = int(duration_str[:-len(unit)])
                    return number * multiplier
                except ValueError:
                    continue
                    
        return None
        
    async def get_audit_log_entry(self, guild: discord.Guild, action: discord.AuditLogAction, 
                                 target_id: int, limit: int = 50) -> Optional[discord.AuditLogEntry]:
        """Find relevant audit log entry for an action"""
        try:
            async for entry in guild.audit_logs(action=action, limit=limit):
                if entry.target and hasattr(entry.target, 'id') and entry.target.id == target_id:
                    return entry
        except discord.Forbidden:
            pass
        return None
        
    async def create_user_info_embed(self, user_info: dict) -> discord.Embed:
        """Create detailed user information embed"""
        user = user_info['user']
        
        embed = discord.Embed(
            title=f"👤 User Information: {user.name}#{user.discriminator}",
            color=0x0099ff,
            timestamp=discord.utils.utcnow()
        )
        
        embed.set_thumbnail(url=user_info['avatar_url'])
        
        # Basic info
        embed.add_field(
            name="📋 Basic Info",
            value=f"**ID:** `{user.id}`\n"
                  f"**Created:** {user.created_at.strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
                  f"**Account Age:** {user_info['account_age']} days",
            inline=False
        )
        
        if user_info['in_guild']:
            member = user_info['member']
            embed.add_field(
                name="🏠 Server Info",
                value=f"**Joined:** {member.joined_at.strftime('%Y-%m-%d %H:%M:%S') if member.joined_at else 'Unknown'} UTC\n"
                      f"**Server Age:** {user_info['guild_age']} days\n"
                      f"**Top Role:** {user_info['top_role']}\n"
                      f"**Roles:** {len(user_info['roles'])}",
                inline=False
            )
            
            if user_info['is_timed_out']:
                embed.add_field(
                    name="⏰ Timeout Status",
                    value=f"**Timed Out Until:** {user_info['timeout_until'].strftime('%Y-%m-%d %H:%M:%S')} UTC",
                    inline=False
                )
        else:
            embed.add_field(
                name="🏠 Server Info",
                value="User is not in this server",
                inline=False
            )
            
        # Moderation info
        embed.add_field(
            name="⚠️ Moderation",
            value=f"**Warnings:** {user_info['warning_count']}\n"
                  f"**Recent Warnings:** {len(user_info['recent_warnings'])}",
            inline=True
        )
        
        return embed
        
    async def validate_reason(self, reason: str, max_length: int = 512) -> str:
        """Validate and clean moderation reason"""
        if not reason or reason.strip() == "":
            return "No reason provided"
            
        reason = reason.strip()
        if len(reason) > max_length:
            return reason[:max_length-3] + "..."
            
        return reason
        
    async def log_command_usage(self, ctx: commands.Context, command_name: str, 
                              target_user: Optional[discord.User] = None, **kwargs):
        """Log command usage for audit purposes"""
        log_data = {
            'command': command_name,
            'moderator_id': ctx.author.id,
            'moderator_name': str(ctx.author),
            'guild_id': ctx.guild.id,
            'guild_name': ctx.guild.name,
            'channel_id': ctx.channel.id,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        if target_user:
            log_data.update({
                'target_user_id': target_user.id,
                'target_username': str(target_user)
            })
            
        log_data.update(kwargs)
        
        self.bot.logger.info(f"Command executed: {command_name} by {ctx.author} in {ctx.guild.name}")

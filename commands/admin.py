import discord
from discord.ext import commands
from typing import Dict, Any, List, Optional
import json
import asyncio
from datetime import datetime, timedelta

class AdminCommands:
    """
    Administrative utilities and advanced configuration management
    that complement the main AdminCog
    """
    
    def __init__(self, bot):
        self.bot = bot
        
    async def backup_guild_config(self, guild_id: int) -> dict:
        """Create a backup of guild configuration"""
        config = await self.bot.db.get_guild_config(guild_id)
        backup = {
            'guild_id': guild_id,
            'config': config,
            'backup_timestamp': datetime.utcnow().isoformat(),
            'backup_version': '1.0'
        }
        return backup
        
    async def restore_guild_config(self, guild_id: int, backup_data: dict) -> bool:
        """Restore guild configuration from backup"""
        try:
            if backup_data.get('guild_id') != guild_id:
                return False
                
            config = backup_data.get('config', {})
            await self.bot.db.update_guild_config(guild_id, config)
            return True
        except Exception as e:
            self.bot.logger.error(f"Error restoring config: {e}")
            return False
            
    async def get_guild_statistics(self, guild: discord.Guild) -> dict:
        """Get comprehensive guild statistics"""
        try:
            warnings = await self.bot.db.get_moderation_logs(guild.id, limit=1000)
            recent_warnings = [w for w in warnings if 
                             datetime.fromisoformat(w['created_at']) > 
                             datetime.utcnow() - timedelta(days=30)]
            
            member_stats = {
                'total_members': guild.member_count,
                'humans': len([m for m in guild.members if not m.bot]),
                'bots': len([m for m in guild.members if m.bot]),
                'online': len([m for m in guild.members if m.status != discord.Status.offline]),
                'roles': len(guild.roles),
                'channels': len(guild.channels),
                'text_channels': len(guild.text_channels),
                'voice_channels': len(guild.voice_channels),
                'categories': len(guild.categories)
            }
            
            moderation_stats = {
                'total_actions': len(warnings),
                'recent_actions': len(recent_warnings),
                'warns': len([w for w in warnings if w['action'] == 'warn']),
                'timeouts': len([w for w in warnings if w['action'] == 'timeout']),
                'kicks': len([w for w in warnings if w['action'] == 'kick']),
                'bans': len([w for w in warnings if w['action'] == 'ban'])
            }
            
            return {
                'guild_info': {
                    'name': guild.name,
                    'id': guild.id,
                    'owner_id': guild.owner_id,
                    'created_at': guild.created_at.isoformat(),
                    'verification_level': str(guild.verification_level),
                    'features': guild.features
                },
                'member_stats': member_stats,
                'moderation_stats': moderation_stats,
                'generated_at': datetime.utcnow().isoformat()
            }
        except Exception as e:
            self.bot.logger.error(f"Error getting guild stats: {e}")
            return {}
            
    async def create_stats_embed(self, guild: discord.Guild, stats: dict) -> discord.Embed:
        """Create statistics embed"""
        embed = discord.Embed(
            title=f"📊 Server Statistics: {guild.name}",
            color=0x0099ff,
            timestamp=discord.utils.utcnow()
        )
        
        embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
        
        member_stats = stats.get('member_stats', {})
        embed.add_field(
            name="👥 Members",
            value=f"**Total:** {member_stats.get('total_members', 0)}\n"
                  f"**Humans:** {member_stats.get('humans', 0)}\n"
                  f"**Bots:** {member_stats.get('bots', 0)}\n"
                  f"**Online:** {member_stats.get('online', 0)}",
            inline=True
        )
        
        embed.add_field(
            name="🏗️ Structure",
            value=f"**Roles:** {member_stats.get('roles', 0)}\n"
                  f"**Text Channels:** {member_stats.get('text_channels', 0)}\n"
                  f"**Voice Channels:** {member_stats.get('voice_channels', 0)}\n"
                  f"**Categories:** {member_stats.get('categories', 0)}",
            inline=True
        )
        
        mod_stats = stats.get('moderation_stats', {})
        embed.add_field(
            name="🔨 Moderation",
            value=f"**Total Actions:** {mod_stats.get('total_actions', 0)}\n"
                  f"**Recent (30d):** {mod_stats.get('recent_actions', 0)}\n"
                  f"**Warnings:** {mod_stats.get('warns', 0)}\n"
                  f"**Bans:** {mod_stats.get('bans', 0)}",
            inline=True
        )
        
        guild_info = stats.get('guild_info', {})
        embed.add_field(
            name="ℹ️ Server Info",
            value=f"**Created:** {guild_info.get('created_at', 'Unknown')[:10]}\n"
                  f"**Owner:** <@{guild_info.get('owner_id', 0)}>\n"
                  f"**Verification:** {guild_info.get('verification_level', 'Unknown')}\n"
                  f"**Features:** {len(guild_info.get('features', []))}",
            inline=True
        )
        
        return embed
        
    async def export_moderation_data(self, guild_id: int, format_type: str = "json") -> dict:
        """Export moderation data for backup/analysis"""
        try:
            logs = await self.bot.db.get_moderation_logs(guild_id, limit=10000)
            guild_config = await self.bot.db.get_guild_config(guild_id)
            
            export_data = {
                'export_info': {
                    'guild_id': guild_id,
                    'export_timestamp': datetime.utcnow().isoformat(),
                    'format': format_type,
                    'version': '1.0'
                },
                'guild_config': guild_config,
                'moderation_logs': logs,
                'summary': {
                    'total_logs': len(logs),
                    'date_range': {
                        'oldest': logs[-1]['created_at'] if logs else None,
                        'newest': logs[0]['created_at'] if logs else None
                    },
                    'action_counts': {}
                }
            }
            
            # Count actions
            for log in logs:
                action = log['action']
                export_data['summary']['action_counts'][action] = \
                    export_data['summary']['action_counts'].get(action, 0) + 1
                    
            return export_data
        except Exception as e:
            self.bot.logger.error(f"Error exporting data: {e}")
            return {}
            
    async def validate_configuration(self, guild: discord.Guild, config: dict) -> List[str]:
        """Validate guild configuration and return warnings/errors"""
        warnings = []
        
        # Check log channel
        log_channel_id = config.get('log_channel')
        if log_channel_id:
            channel = guild.get_channel(log_channel_id)
            if not channel:
                warnings.append(f"Log channel {log_channel_id} not found or inaccessible")
            elif not channel.permissions_for(guild.me).send_messages:
                warnings.append(f"Bot cannot send messages to log channel {channel.name}")
                
        # Check welcome channel
        welcome_channel_id = config.get('welcome_channel')
        if welcome_channel_id and config.get('welcome_enabled', False):
            channel = guild.get_channel(welcome_channel_id)
            if not channel:
                warnings.append(f"Welcome channel {welcome_channel_id} not found or inaccessible")
            elif not channel.permissions_for(guild.me).send_messages:
                warnings.append(f"Bot cannot send messages to welcome channel {channel.name}")
                
        # Check warning limits
        max_warnings = config.get('max_warnings', 3)
        if max_warnings < 1 or max_warnings > 10:
            warnings.append(f"Max warnings ({max_warnings}) should be between 1 and 10")
            
        # Check timeout duration
        timeout_duration = config.get('timeout_duration', 300)
        if timeout_duration < 60 or timeout_duration > 2419200:
            warnings.append(f"Timeout duration ({timeout_duration}s) should be between 60s and 28 days")
            
        return warnings
        
    async def get_role_hierarchy(self, guild: discord.Guild) -> List[dict]:
        """Get formatted role hierarchy information"""
        roles = []
        for role in sorted(guild.roles, key=lambda r: r.position, reverse=True):
            if role.name == '@everyone':
                continue
                
            roles.append({
                'name': role.name,
                'id': role.id,
                'position': role.position,
                'color': str(role.color),
                'permissions': role.permissions.value,
                'mentionable': role.mentionable,
                'hoisted': role.hoist,
                'managed': role.managed,
                'member_count': len(role.members)
            })
            
        return roles
        
    async def analyze_permissions(self, guild: discord.Guild) -> dict:
        """Analyze potentially dangerous permissions in the guild"""
        dangerous_perms = [
            'administrator', 'manage_guild', 'manage_roles', 'manage_channels',
            'kick_members', 'ban_members', 'manage_messages', 'manage_webhooks',
            'manage_nicknames', 'moderate_members'
        ]
        
        analysis = {
            'dangerous_roles': [],
            'privileged_members': [],
            'bot_permissions': {},
            'warnings': []
        }
        
        # Check roles with dangerous permissions
        for role in guild.roles:
            if role.name == '@everyone':
                continue
                
            role_perms = []
            for perm in dangerous_perms:
                if getattr(role.permissions, perm, False):
                    role_perms.append(perm)
                    
            if role_perms:
                analysis['dangerous_roles'].append({
                    'role': role.name,
                    'id': role.id,
                    'permissions': role_perms,
                    'member_count': len(role.members)
                })
                
        # Check members with elevated permissions
        for member in guild.members:
            if member.bot:
                continue
                
            member_perms = []
            for perm in dangerous_perms:
                if getattr(member.guild_permissions, perm, False):
                    member_perms.append(perm)
                    
            if member_perms and not member.guild_permissions.administrator:
                analysis['privileged_members'].append({
                    'member': str(member),
                    'id': member.id,
                    'permissions': member_perms
                })
                
        # Check bot permissions
        bot_member = guild.me
        for perm in dangerous_perms:
            analysis['bot_permissions'][perm] = getattr(bot_member.guild_permissions, perm, False)
            
        # Generate warnings
        if len(analysis['dangerous_roles']) > 5:
            analysis['warnings'].append("Many roles have dangerous permissions")
            
        if any(role['member_count'] > 10 for role in analysis['dangerous_roles']):
            analysis['warnings'].append("Some dangerous roles have many members")
            
        return analysis
        
    async def create_permissions_embed(self, guild: discord.Guild, analysis: dict) -> discord.Embed:
        """Create permissions analysis embed"""
        embed = discord.Embed(
            title=f"🔐 Permissions Analysis: {guild.name}",
            color=0xff9900 if analysis['warnings'] else 0x00ff00,
            timestamp=discord.utils.utcnow()
        )
        
        if analysis['warnings']:
            embed.add_field(
                name="⚠️ Warnings",
                value='\n'.join(f"• {warning}" for warning in analysis['warnings']),
                inline=False
            )
            
        dangerous_roles = analysis['dangerous_roles'][:5]  # Limit to 5
        if dangerous_roles:
            role_list = []
            for role_info in dangerous_roles:
                role_list.append(f"**{role_info['role']}** ({role_info['member_count']} members)")
                
            embed.add_field(
                name="🎭 Privileged Roles",
                value='\n'.join(role_list) or "None",
                inline=True
            )
            
        bot_perms = analysis['bot_permissions']
        missing_perms = [perm for perm, has_perm in bot_perms.items() if not has_perm]
        
        embed.add_field(
            name="🤖 Bot Permissions",
            value=f"**Has:** {len(bot_perms) - len(missing_perms)}\n"
                  f"**Missing:** {len(missing_perms)}",
            inline=True
        )
        
        if missing_perms:
            embed.add_field(
                name="❌ Missing Permissions",
                value='\n'.join(f"• {perm.replace('_', ' ').title()}" for perm in missing_perms[:5]),
                inline=False
            )
            
        return embed
        
    async def cleanup_old_data(self, days: int = 30) -> dict:
        """Clean up old moderation data"""
        try:
            await self.bot.db.cleanup_old_data()
            
            cleanup_result = {
                'success': True,
                'cleaned_at': datetime.utcnow().isoformat(),
                'days_threshold': days,
                'message': f"Cleaned up data older than {days} days"
            }
            
            self.bot.logger.info(f"Database cleanup completed for data older than {days} days")
            return cleanup_result
            
        except Exception as e:
            self.bot.logger.error(f"Error during cleanup: {e}")
            return {
                'success': False,
                'error': str(e),
                'cleaned_at': datetime.utcnow().isoformat()
            }

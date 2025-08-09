import discord
from discord.ext import commands
from utils.permissions import has_mod_permissions, can_moderate_user, check_bot_permissions
from utils.logging import ModerationLogger
from datetime import datetime, timedelta
import asyncio

class ModerationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = ModerationLogger(bot)
        
    @commands.command(name='warn')
    @has_mod_permissions()
    async def warn_user(self, ctx, user: discord.Member, *, reason: str = "No reason provided"):
        if not await can_moderate_user(ctx.author, user):
            embed = discord.Embed(
                title="❌ Permission Denied",
                description="You cannot moderate this user.",
                color=0xff0000
            )
            await ctx.send(embed=embed, delete_after=10)
            return
            
        await self.bot.db.add_warning(ctx.guild.id, user.id, ctx.author.id, reason)
        warnings = await self.bot.db.get_user_warnings(ctx.guild.id, user.id)
        warning_count = len(warnings)
        
        embed = discord.Embed(
            title="⚠️ User Warned",
            description=f"{user.mention} has been warned.",
            color=0xff9900,
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Total Warnings", value=str(warning_count), inline=True)
        embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
        
        await ctx.send(embed=embed)
        
        try:
            dm_embed = discord.Embed(
                title=f"⚠️ Warning from {ctx.guild.name}",
                description=f"You have been warned by {ctx.author.name}.",
                color=0xff9900
            )
            dm_embed.add_field(name="Reason", value=reason, inline=False)
            dm_embed.add_field(name="Total Warnings", value=str(warning_count), inline=True)
            await user.send(embed=dm_embed)
        except discord.Forbidden:
            pass
            
        await self.bot.db.log_moderation_action(
            ctx.guild.id, user.id, ctx.author.id, "warn", reason
        )
        
        await self.logger.log_action(ctx.guild.id, {
            'action': 'warn',
            'user_id': user.id,
            'moderator_id': ctx.author.id,
            'reason': reason,
            'warning_count': warning_count
        })
        
    @commands.command(name='warnings')
    @has_mod_permissions()
    async def view_warnings(self, ctx, user: discord.Member):
        warnings = await self.bot.db.get_user_warnings(ctx.guild.id, user.id)
        
        if not warnings:
            embed = discord.Embed(
                title="📋 User Warnings",
                description=f"{user.mention} has no warnings.",
                color=0x00ff00
            )
            await ctx.send(embed=embed)
            return
            
        embed = discord.Embed(
            title="📋 User Warnings",
            description=f"Warnings for {user.mention}",
            color=0xff9900
        )
        
        for i, warning in enumerate(warnings[:10], 1):
            moderator = self.bot.get_user(warning['moderator_id'])
            mod_name = moderator.name if moderator else f"Unknown ({warning['moderator_id']})"
            
            embed.add_field(
                name=f"Warning #{i}",
                value=f"**Reason:** {warning['reason']}\n"
                      f"**Moderator:** {mod_name}\n"
                      f"**Date:** {warning['created_at'][:10]}",
                inline=False
            )
            
        if len(warnings) > 10:
            embed.set_footer(text=f"Showing 10 of {len(warnings)} warnings")
            
        await ctx.send(embed=embed)
        
    @commands.command(name='unwarn')
    @has_mod_permissions()
    async def remove_warning(self, ctx, warning_id: int):
        success = await self.bot.db.remove_warning(warning_id)
        
        if success:
            embed = discord.Embed(
                title="✅ Warning Removed",
                description=f"Warning #{warning_id} has been removed.",
                color=0x00ff00
            )
        else:
            embed = discord.Embed(
                title="❌ Warning Not Found",
                description=f"Warning #{warning_id} could not be found.",
                color=0xff0000
            )
            
        await ctx.send(embed=embed, delete_after=10)
        
    @commands.command(name='clearwarns')
    @has_mod_permissions()
    async def clear_warnings(self, ctx, user: discord.Member):
        if not await can_moderate_user(ctx.author, user):
            embed = discord.Embed(
                title="❌ Permission Denied",
                description="You cannot moderate this user.",
                color=0xff0000
            )
            await ctx.send(embed=embed, delete_after=10)
            return
            
        await self.bot.db.clear_user_warnings(ctx.guild.id, user.id)
        
        embed = discord.Embed(
            title="✅ Warnings Cleared",
            description=f"All warnings for {user.mention} have been cleared.",
            color=0x00ff00
        )
        await ctx.send(embed=embed)
        
        await self.logger.log_action(ctx.guild.id, {
            'action': 'unwarn',
            'user_id': user.id,
            'moderator_id': ctx.author.id,
            'reason': 'All warnings cleared'
        })
        
    @commands.command(name='timeout')
    @has_mod_permissions()
    async def timeout_user(self, ctx, user: discord.Member, duration: int, *, reason: str = "No reason provided"):
        if not await can_moderate_user(ctx.author, user):
            embed = discord.Embed(
                title="❌ Permission Denied",
                description="You cannot moderate this user.",
                color=0xff0000
            )
            await ctx.send(embed=embed, delete_after=10)
            return
            
        missing_perms = await check_bot_permissions(ctx.channel, ['moderate_members'])
        if missing_perms:
            embed = discord.Embed(
                title="❌ Missing Permissions",
                description="I need the 'Timeout Members' permission to use this command.",
                color=0xff0000
            )
            await ctx.send(embed=embed, delete_after=10)
            return
            
        if duration > 2419200:  # 28 days max
            embed = discord.Embed(
                title="❌ Invalid Duration",
                description="Timeout duration cannot exceed 28 days (2419200 seconds).",
                color=0xff0000
            )
            await ctx.send(embed=embed, delete_after=10)
            return
            
        try:
            timeout_until = discord.utils.utcnow() + timedelta(seconds=duration)
            await user.timeout(timeout_until, reason=reason)
            
            embed = discord.Embed(
                title="⏰ User Timed Out",
                description=f"{user.mention} has been timed out.",
                color=0xff6600,
                timestamp=discord.utils.utcnow()
            )
            embed.add_field(name="Duration", value=f"{duration} seconds", inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
            
            await ctx.send(embed=embed)
            
            try:
                dm_embed = discord.Embed(
                    title=f"⏰ Timeout from {ctx.guild.name}",
                    description=f"You have been timed out by {ctx.author.name}.",
                    color=0xff6600
                )
                dm_embed.add_field(name="Duration", value=f"{duration} seconds", inline=True)
                dm_embed.add_field(name="Reason", value=reason, inline=False)
                await user.send(embed=dm_embed)
            except discord.Forbidden:
                pass
                
            await self.bot.db.log_moderation_action(
                ctx.guild.id, user.id, ctx.author.id, "timeout", reason, duration
            )
            
            await self.logger.log_action(ctx.guild.id, {
                'action': 'timeout',
                'user_id': user.id,
                'moderator_id': ctx.author.id,
                'reason': reason,
                'duration': duration
            })
            
        except discord.Forbidden:
            embed = discord.Embed(
                title="❌ Permission Error",
                description="I don't have permission to timeout this user.",
                color=0xff0000
            )
            await ctx.send(embed=embed, delete_after=10)
            
    @commands.command(name='untimeout')
    @has_mod_permissions()
    async def remove_timeout(self, ctx, user: discord.Member, *, reason: str = "No reason provided"):
        if not user.is_timed_out():
            embed = discord.Embed(
                title="❌ User Not Timed Out",
                description=f"{user.mention} is not currently timed out.",
                color=0xff0000
            )
            await ctx.send(embed=embed, delete_after=10)
            return
            
        try:
            await user.timeout(None, reason=reason)
            
            embed = discord.Embed(
                title="✅ Timeout Removed",
                description=f"Timeout removed for {user.mention}.",
                color=0x00ff00
            )
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
            
            await ctx.send(embed=embed)
            
            await self.logger.log_action(ctx.guild.id, {
                'action': 'untimeout',
                'user_id': user.id,
                'moderator_id': ctx.author.id,
                'reason': reason
            })
            
        except discord.Forbidden:
            embed = discord.Embed(
                title="❌ Permission Error",
                description="I don't have permission to remove timeout from this user.",
                color=0xff0000
            )
            await ctx.send(embed=embed, delete_after=10)
            
    @commands.command(name='kick')
    @has_mod_permissions()
    async def kick_user(self, ctx, user: discord.Member, *, reason: str = "No reason provided"):
        if not await can_moderate_user(ctx.author, user):
            embed = discord.Embed(
                title="❌ Permission Denied",
                description="You cannot moderate this user.",
                color=0xff0000
            )
            await ctx.send(embed=embed, delete_after=10)
            return
            
        missing_perms = await check_bot_permissions(ctx.channel, ['kick_members'])
        if missing_perms:
            embed = discord.Embed(
                title="❌ Missing Permissions",
                description="I need the 'Kick Members' permission to use this command.",
                color=0xff0000
            )
            await ctx.send(embed=embed, delete_after=10)
            return
            
        try:
            dm_embed = discord.Embed(
                title=f"👢 Kicked from {ctx.guild.name}",
                description=f"You have been kicked by {ctx.author.name}.",
                color=0xff3300
            )
            dm_embed.add_field(name="Reason", value=reason, inline=False)
            
            try:
                await user.send(embed=dm_embed)
            except discord.Forbidden:
                pass
                
            await user.kick(reason=reason)
            
            embed = discord.Embed(
                title="👢 User Kicked",
                description=f"{user.name}#{user.discriminator} has been kicked.",
                color=0xff3300,
                timestamp=discord.utils.utcnow()
            )
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
            
            await ctx.send(embed=embed)
            
            await self.bot.db.log_moderation_action(
                ctx.guild.id, user.id, ctx.author.id, "kick", reason
            )
            
            await self.logger.log_action(ctx.guild.id, {
                'action': 'kick',
                'user_id': user.id,
                'moderator_id': ctx.author.id,
                'reason': reason
            })
            
        except discord.Forbidden:
            embed = discord.Embed(
                title="❌ Permission Error",
                description="I don't have permission to kick this user.",
                color=0xff0000
            )
            await ctx.send(embed=embed, delete_after=10)
            
    @commands.command(name='ban')
    @has_mod_permissions()
    async def ban_user(self, ctx, user: discord.Member, delete_days: int = 0, *, reason: str = "No reason provided"):
        if not await can_moderate_user(ctx.author, user):
            embed = discord.Embed(
                title="❌ Permission Denied",
                description="You cannot moderate this user.",
                color=0xff0000
            )
            await ctx.send(embed=embed, delete_after=10)
            return
            
        missing_perms = await check_bot_permissions(ctx.channel, ['ban_members'])
        if missing_perms:
            embed = discord.Embed(
                title="❌ Missing Permissions",
                description="I need the 'Ban Members' permission to use this command.",
                color=0xff0000
            )
            await ctx.send(embed=embed, delete_after=10)
            return
            
        if delete_days < 0 or delete_days > 7:
            embed = discord.Embed(
                title="❌ Invalid Parameter",
                description="Delete days must be between 0 and 7.",
                color=0xff0000
            )
            await ctx.send(embed=embed, delete_after=10)
            return
            
        try:
            dm_embed = discord.Embed(
                title=f"🔨 Banned from {ctx.guild.name}",
                description=f"You have been banned by {ctx.author.name}.",
                color=0xff0000
            )
            dm_embed.add_field(name="Reason", value=reason, inline=False)
            
            try:
                await user.send(embed=dm_embed)
            except discord.Forbidden:
                pass
                
            await user.ban(reason=reason, delete_message_days=delete_days)
            
            embed = discord.Embed(
                title="🔨 User Banned",
                description=f"{user.name}#{user.discriminator} has been banned.",
                color=0xff0000,
                timestamp=discord.utils.utcnow()
            )
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.add_field(name="Messages Deleted", value=f"{delete_days} days", inline=True)
            embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
            
            await ctx.send(embed=embed)
            
            await self.bot.db.log_moderation_action(
                ctx.guild.id, user.id, ctx.author.id, "ban", reason
            )
            
            await self.logger.log_action(ctx.guild.id, {
                'action': 'ban',
                'user_id': user.id,
                'moderator_id': ctx.author.id,
                'reason': reason
            })
            
        except discord.Forbidden:
            embed = discord.Embed(
                title="❌ Permission Error",
                description="I don't have permission to ban this user.",
                color=0xff0000
            )
            await ctx.send(embed=embed, delete_after=10)
            
    @commands.command(name='unban')
    @has_mod_permissions()
    async def unban_user(self, ctx, user_id: int, *, reason: str = "No reason provided"):
        missing_perms = await check_bot_permissions(ctx.channel, ['ban_members'])
        if missing_perms:
            embed = discord.Embed(
                title="❌ Missing Permissions",
                description="I need the 'Ban Members' permission to use this command.",
                color=0xff0000
            )
            await ctx.send(embed=embed, delete_after=10)
            return
            
        try:
            banned_users = [ban_entry async for ban_entry in ctx.guild.bans(limit=2000)]
            banned_user = None
            
            for ban_entry in banned_users:
                if ban_entry.user.id == user_id:
                    banned_user = ban_entry.user
                    break
                    
            if not banned_user:
                embed = discord.Embed(
                    title="❌ User Not Banned",
                    description=f"User with ID {user_id} is not banned from this server.",
                    color=0xff0000
                )
                await ctx.send(embed=embed, delete_after=10)
                return
                
            await ctx.guild.unban(banned_user, reason=reason)
            
            embed = discord.Embed(
                title="✅ User Unbanned",
                description=f"{banned_user.name}#{banned_user.discriminator} has been unbanned.",
                color=0x00ff00,
                timestamp=discord.utils.utcnow()
            )
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
            
            await ctx.send(embed=embed)
            
            await self.bot.db.log_moderation_action(
                ctx.guild.id, user_id, ctx.author.id, "unban", reason
            )
            
            await self.logger.log_action(ctx.guild.id, {
                'action': 'unban',
                'user_id': user_id,
                'moderator_id': ctx.author.id,
                'reason': reason
            })
            
        except discord.Forbidden:
            embed = discord.Embed(
                title="❌ Permission Error",
                description="I don't have permission to unban users.",
                color=0xff0000
            )
            await ctx.send(embed=embed, delete_after=10)
        except discord.NotFound:
            embed = discord.Embed(
                title="❌ User Not Found",
                description=f"User with ID {user_id} was not found in the ban list.",
                color=0xff0000
            )
            await ctx.send(embed=embed, delete_after=10)
            
    @commands.command(name='purge', aliases=['clear'])
    @has_mod_permissions()
    async def purge_messages(self, ctx, amount: int, user: discord.Member = None):
        if amount < 1 or amount > 1000:
            embed = discord.Embed(
                title="❌ Invalid Amount",
                description="Amount must be between 1 and 1000.",
                color=0xff0000
            )
            await ctx.send(embed=embed, delete_after=10)
            return
            
        missing_perms = await check_bot_permissions(ctx.channel, ['manage_messages'])
        if missing_perms:
            embed = discord.Embed(
                title="❌ Missing Permissions",
                description="I need the 'Manage Messages' permission to use this command.",
                color=0xff0000
            )
            await ctx.send(embed=embed, delete_after=10)
            return
            
        try:
            await ctx.message.delete()
            
            if user:
                def check(message):
                    return message.author == user
                deleted = await ctx.channel.purge(limit=amount, check=check)
            else:
                deleted = await ctx.channel.purge(limit=amount)
                
            embed = discord.Embed(
                title="🗑️ Messages Purged",
                description=f"Deleted {len(deleted)} messages" + 
                           (f" from {user.mention}" if user else ""),
                color=0x9900ff
            )
            embed.set_footer(text="This message will be deleted in 10 seconds")
            
            await ctx.send(embed=embed, delete_after=10)
            
            await self.bot.db.log_moderation_action(
                ctx.guild.id, 
                user.id if user else None, 
                ctx.author.id, 
                "purge", 
                f"Purged {len(deleted)} messages" + (f" from {user.name}" if user else "")
            )
            
            await self.logger.log_action(ctx.guild.id, {
                'action': 'purge',
                'user_id': user.id if user else None,
                'moderator_id': ctx.author.id,
                'reason': f"Purged {len(deleted)} messages"
            })
            
        except discord.Forbidden:
            embed = discord.Embed(
                title="❌ Permission Error",
                description="I don't have permission to delete messages.",
                color=0xff0000
            )
            await ctx.send(embed=embed, delete_after=10)

async def setup(bot):
    await bot.add_cog(ModerationCog(bot))

import discord
from discord.ext import commands
from utils.permissions import has_admin_permissions
import json

class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @commands.group(name='config', invoke_without_command=True)
    @has_admin_permissions()
    async def config_group(self, ctx):
        guild_config = await self.bot.db.get_guild_config(ctx.guild.id)
        
        embed = discord.Embed(
            title="⚙️ Server Configuration",
            description="Current server settings",
            color=0x0099ff
        )
        
        embed.add_field(
            name="Auto-Moderation",
            value=f"Enabled: {guild_config.get('automod_enabled', True)}\n"
                  f"Spam Detection: {guild_config.get('spam_detection', True)}\n"
                  f"Profanity Filter: {guild_config.get('profanity_filter', True)}",
            inline=False
        )
        
        embed.add_field(
            name="Warning System",
            value=f"Max Warnings: {guild_config.get('max_warnings', 3)}\n"
                  f"Timeout Duration: {guild_config.get('timeout_duration', 300)}s",
            inline=True
        )
        
        embed.add_field(
            name="Logging",
            value=f"Channel: <#{guild_config.get('log_channel')}>" if guild_config.get('log_channel') else "Not Set",
            inline=True
        )
        
        embed.add_field(
            name="Welcome System",
            value=f"Enabled: {guild_config.get('welcome_enabled', False)}\n"
                  f"Channel: <#{guild_config.get('welcome_channel')}>" if guild_config.get('welcome_channel') else "Not Set",
            inline=False
        )
        
        embed.set_footer(text=f"Use {ctx.prefix}config <setting> to modify settings")
        
        await ctx.send(embed=embed)
        
    @config_group.command(name='logchannel')
    @has_admin_permissions()
    async def set_log_channel(self, ctx, channel: discord.TextChannel):
        guild_config = await self.bot.db.get_guild_config(ctx.guild.id)
        guild_config['log_channel'] = channel.id
        await self.bot.db.update_guild_config(ctx.guild.id, guild_config)
        
        embed = discord.Embed(
            title="✅ Log Channel Set",
            description=f"Moderation logs will now be sent to {channel.mention}",
            color=0x00ff00
        )
        await ctx.send(embed=embed)
        
    @config_group.command(name='welcomechannel')
    @has_admin_permissions()
    async def set_welcome_channel(self, ctx, channel: discord.TextChannel):
        guild_config = await self.bot.db.get_guild_config(ctx.guild.id)
        guild_config['welcome_channel'] = channel.id
        guild_config['welcome_enabled'] = True
        await self.bot.db.update_guild_config(ctx.guild.id, guild_config)
        
        embed = discord.Embed(
            title="✅ Welcome Channel Set",
            description=f"Welcome messages will now be sent to {channel.mention}",
            color=0x00ff00
        )
        await ctx.send(embed=embed)
        
    @config_group.command(name='welcomemessage')
    @has_admin_permissions()
    async def set_welcome_message(self, ctx, *, message: str):
        guild_config = await self.bot.db.get_guild_config(ctx.guild.id)
        guild_config['welcome_message'] = message
        await self.bot.db.update_guild_config(ctx.guild.id, guild_config)
        
        embed = discord.Embed(
            title="✅ Welcome Message Set",
            description=f"New welcome message: {message}",
            color=0x00ff00
        )
        await ctx.send(embed=embed)
        
    @config_group.command(name='automod')
    @has_admin_permissions()
    async def toggle_automod(self, ctx, enabled: bool):
        guild_config = await self.bot.db.get_guild_config(ctx.guild.id)
        guild_config['automod_enabled'] = enabled
        await self.bot.db.update_guild_config(ctx.guild.id, guild_config)
        
        status = "enabled" if enabled else "disabled"
        embed = discord.Embed(
            title=f"✅ Auto-Moderation {status.title()}",
            description=f"Auto-moderation has been {status}",
            color=0x00ff00 if enabled else 0xff9900
        )
        await ctx.send(embed=embed)
        
    @config_group.command(name='maxwarnings')
    @has_admin_permissions()
    async def set_max_warnings(self, ctx, amount: int):
        if amount < 1 or amount > 10:
            embed = discord.Embed(
                title="❌ Invalid Amount",
                description="Max warnings must be between 1 and 10",
                color=0xff0000
            )
            await ctx.send(embed=embed, delete_after=10)
            return
            
        guild_config = await self.bot.db.get_guild_config(ctx.guild.id)
        guild_config['max_warnings'] = amount
        await self.bot.db.update_guild_config(ctx.guild.id, guild_config)
        
        embed = discord.Embed(
            title="✅ Max Warnings Updated",
            description=f"Maximum warnings set to {amount}",
            color=0x00ff00
        )
        await ctx.send(embed=embed)
        
    @config_group.command(name='timeoutduration')
    @has_admin_permissions()
    async def set_timeout_duration(self, ctx, seconds: int):
        if seconds < 60 or seconds > 2419200:  # 1 minute to 28 days
            embed = discord.Embed(
                title="❌ Invalid Duration",
                description="Timeout duration must be between 60 seconds and 28 days",
                color=0xff0000
            )
            await ctx.send(embed=embed, delete_after=10)
            return
            
        guild_config = await self.bot.db.get_guild_config(ctx.guild.id)
        guild_config['timeout_duration'] = seconds
        await self.bot.db.update_guild_config(ctx.guild.id, guild_config)
        
        embed = discord.Embed(
            title="✅ Timeout Duration Updated",
            description=f"Default timeout duration set to {seconds} seconds",
            color=0x00ff00
        )
        await ctx.send(embed=embed)
        
    @commands.command(name='modlogs')
    @has_admin_permissions()
    async def view_mod_logs(self, ctx, limit: int = 10):
        if limit < 1 or limit > 50:
            limit = 10
            
        logs = await self.bot.db.get_moderation_logs(ctx.guild.id, limit)
        
        if not logs:
            embed = discord.Embed(
                title="📋 Moderation Logs",
                description="No moderation logs found",
                color=0x808080
            )
            await ctx.send(embed=embed)
            return
            
        embed = discord.Embed(
            title="📋 Moderation Logs",
            description=f"Last {len(logs)} moderation actions",
            color=0x0099ff
        )
        
        for log in logs:
            user = self.bot.get_user(log['user_id'])
            moderator = self.bot.get_user(log['moderator_id'])
            
            user_name = user.name if user else f"Unknown ({log['user_id']})"
            mod_name = moderator.name if moderator else f"Unknown ({log['moderator_id']})"
            
            embed.add_field(
                name=f"{log['action'].title()} - {log['created_at'][:16]}",
                value=f"**User:** {user_name}\n"
                      f"**Moderator:** {mod_name}\n"
                      f"**Reason:** {log['reason'][:100]}{'...' if len(log['reason']) > 100 else ''}",
                inline=False
            )
            
        await ctx.send(embed=embed)
        
    @commands.command(name='help')
    async def help_command(self, ctx):
        embed = discord.Embed(
            title="🤖 Moderation Bot Help",
            description="Advanced Discord moderation bot with automated features",
            color=0x0099ff
        )
        
        embed.add_field(
            name="🔨 Moderation Commands",
            value=f"`{ctx.prefix}warn <user> <reason>` - Warn a user\n"
                  f"`{ctx.prefix}timeout <user> <seconds> <reason>` - Timeout a user\n"
                  f"`{ctx.prefix}kick <user> <reason>` - Kick a user\n"
                  f"`{ctx.prefix}ban <user> [delete_days] <reason>` - Ban a user\n"
                  f"`{ctx.prefix}unban <user_id> <reason>` - Unban a user\n"
                  f"`{ctx.prefix}purge <amount> [user]` - Delete messages",
            inline=False
        )
        
        embed.add_field(
            name="📋 Information Commands",
            value=f"`{ctx.prefix}warnings <user>` - View user warnings\n"
                  f"`{ctx.prefix}modlogs [limit]` - View moderation logs\n"
                  f"`{ctx.prefix}config` - View server configuration",
            inline=False
        )
        
        embed.add_field(
            name="⚙️ Configuration Commands",
            value=f"`{ctx.prefix}config logchannel <channel>` - Set log channel\n"
                  f"`{ctx.prefix}config welcomechannel <channel>` - Set welcome channel\n"
                  f"`{ctx.prefix}config automod <true/false>` - Toggle auto-mod\n"
                  f"`{ctx.prefix}config maxwarnings <amount>` - Set max warnings",
            inline=False
        )
        
        embed.add_field(
            name="🔧 Warning Management",
            value=f"`{ctx.prefix}unwarn <warning_id>` - Remove a warning\n"
                  f"`{ctx.prefix}clearwarns <user>` - Clear all user warnings",
            inline=False
        )
        
        embed.set_footer(text="Auto-moderation features include spam detection, profanity filtering, and automated actions")
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(AdminCog(bot))

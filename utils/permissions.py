import discord
from discord.ext import commands
from typing import List, Union
import json

def has_mod_permissions():
    async def predicate(ctx):
        if ctx.author.guild_permissions.administrator:
            return True
            
        with open('config.json', 'r') as f:
            config = json.load(f)
            
        mod_roles = config.get('moderation_roles', [])
        
        for role in ctx.author.roles:
            if role.name in mod_roles:
                return True
                
        return False
        
    return commands.check(predicate)

def has_admin_permissions():
    async def predicate(ctx):
        return ctx.author.guild_permissions.administrator
        
    return commands.check(predicate)

async def can_moderate_user(moderator: discord.Member, target: discord.Member) -> bool:
    if moderator.guild_permissions.administrator:
        return True
        
    if target.guild_permissions.administrator:
        return False
        
    if moderator.top_role <= target.top_role:
        return False
        
    return True

async def get_higher_role_members(guild: discord.Guild, role_threshold: discord.Role) -> List[discord.Member]:
    members = []
    for member in guild.members:
        if member.top_role >= role_threshold and not member.bot:
            members.append(member)
    return members

class PermissionError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

async def check_bot_permissions(channel: discord.TextChannel, permissions: List[str]) -> List[str]:
    missing = []
    bot_permissions = channel.permissions_for(channel.guild.me)
    
    for perm in permissions:
        if not getattr(bot_permissions, perm, False):
            missing.append(perm)
            
    return missing

async def format_permissions(permissions: List[str]) -> str:
    formatted = []
    for perm in permissions:
        formatted.append(perm.replace('_', ' ').title())
    return ', '.join(formatted)

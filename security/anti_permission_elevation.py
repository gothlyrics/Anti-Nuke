import discord
from discord.ext import commands
from datetime import datetime
from typing import Optional

class AntiPermissionElevation:
    def __init__(self, bot: commands.Bot, db, config, moderator_logs):
        self.bot = bot
        self.db = db
        self.config = config
        self.moderator_logs = moderator_logs
        self.owner_id = 1329899250758451300

    async def check_role_update(self, before: discord.Role, after: discord.Role) -> bool:
        """Проверка обновления роли на повышение прав"""
        if after.guild.me.guild_permissions.view_audit_log:
            async for entry in after.guild.audit_logs(action=discord.AuditLogAction.role_update, limit=1):
                if entry.user and entry.user.id != self.owner_id and entry.user.id != self.bot.user.id:
                    # Проверка, повысил ли модератор права
                    if await self.is_permission_elevation(before, after, entry.user):
                        # Отмена действия
                        try:
                            await after.edit(permissions=before.permissions, reason="Anti-Permission Elevation: Отмена повышения прав")
                            await self.moderator_logs.log_moderator_action(
                                after.guild,
                                "permission_elevation_blocked",
                                entry.user,
                                None,
                                "Попытка повышения прав",
                                f"Роль: {after.name}"
                            )
                            return False
                        except:
                            pass
                    break
        return True

    async def check_member_role_add(self, member: discord.Member, role: discord.Role, moderator: discord.Member) -> bool:
        """Проверка выдачи роли на повышение прав"""
        if moderator.id == self.owner_id:
            return True
        
        # Проверка, повышает ли роль права модератора
        if role.permissions.administrator or role.permissions.manage_guild:
            # Отмена действия
            try:
                await member.remove_roles(role, reason="Anti-Permission Elevation: Отмена повышения прав")
                await self.moderator_logs.log_moderator_action(
                    member.guild,
                    "permission_elevation_blocked",
                    moderator,
                    member,
                    "Попытка выдать опасную роль",
                    f"Роль: {role.name}"
                )
                return False
            except:
                pass
        
        return True

    async def is_permission_elevation(self, before: discord.Role, after: discord.Role, user: discord.Member) -> bool:
        """Проверка, является ли это повышением прав"""
        # Проверка на добавление опасных прав
        dangerous_perms = [
            'administrator',
            'manage_guild',
            'manage_roles',
            'manage_channels'
        ]
        
        before_perms = before.permissions
        after_perms = after.permissions
        
        for perm in dangerous_perms:
            if not getattr(before_perms, perm) and getattr(after_perms, perm):
                # Право было добавлено
                return True
        
        return False




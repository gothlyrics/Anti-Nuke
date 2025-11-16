import discord
from discord.ext import commands
from datetime import datetime
from typing import Dict

class OwnerLock:
    def __init__(self, bot: commands.Bot, db, config):
        self.bot = bot
        self.db = db
        self.config = config
        self.owner_id = 1329899250758451300
        self.locked_guilds: Dict[int, bool] = {}  # {guild_id: bool}
        self.saved_permissions: Dict[int, Dict] = {}  # {guild_id: {role_id: permissions}}

    async def enable_owner_lock(self, guild: discord.Guild):
        """Включение Owner Lock"""
        self.locked_guilds[guild.id] = True
        
        # Сохранение текущих прав модераторов
        admin_role_ids = self.config.get("roles", "admin", default=[])
        if isinstance(admin_role_ids, str):
            admin_role_ids = [admin_role_ids]
        elif not isinstance(admin_role_ids, list):
            admin_role_ids = []
        
        saved_perms = {}
        for role_id_str in admin_role_ids:
            try:
                role_id = int(role_id_str)
                role = guild.get_role(role_id)
                if role:
                    saved_perms[role_id] = {
                        "permissions": role.permissions.value,
                        "name": role.name
                    }
            except:
                pass
        
        # Также сохраняем права администраторов
        for member in guild.members:
            if member.guild_permissions.administrator and member.id != self.owner_id:
                # Сохраняем их права через роли
                for role in member.roles:
                    if role.id not in saved_perms:
                        saved_perms[role.id] = {
                            "permissions": role.permissions.value,
                            "name": role.name
                        }
        
        self.saved_permissions[guild.id] = saved_perms
        
        # Удаление опасных прав у модераторов
        dangerous_permissions = discord.Permissions(
            manage_guild=True,
            manage_roles=True,
            manage_channels=True,
            administrator=True,
            ban_members=True,
            kick_members=True,
            manage_messages=True
        )
        
        for role_id_str in admin_role_ids:
            try:
                role_id = int(role_id_str)
                role = guild.get_role(role_id)
                if role:
                    # Удаление опасных прав
                    new_perms = role.permissions
                    new_perms.update(manage_guild=False, manage_roles=False, manage_channels=False,
                                    administrator=False, ban_members=False, kick_members=False,
                                    manage_messages=False)
                    await role.edit(permissions=new_perms, reason="Owner Lock: Блокировка опасных прав")
            except:
                pass
        
        await self.log_owner_lock(guild, "enabled", "Owner Lock активирован")

    async def disable_owner_lock(self, guild: discord.Guild):
        """Отключение Owner Lock"""
        self.locked_guilds[guild.id] = False
        
        # Восстановление прав (опционально, можно оставить заблокированными)
        # saved_perms = self.saved_permissions.get(guild.id, {})
        # for role_id, perm_data in saved_perms.items():
        #     role = guild.get_role(role_id)
        #     if role:
        #         await role.edit(permissions=discord.Permissions(perm_data["permissions"]))
        
        await self.log_owner_lock(guild, "disabled", "Owner Lock отключен")

    def is_locked(self, guild_id: int) -> bool:
        """Проверка, заблокирован ли сервер"""
        return self.locked_guilds.get(guild_id, False)

    async def log_owner_lock(self, guild: discord.Guild, action: str, details: str):
        """Логирование Owner Lock"""
        log_channel_id = self.config.get_channel("security_logs")
        if not log_channel_id:
            return

        log_channel = guild.get_channel(int(log_channel_id))
        if not log_channel:
            return

        embed = discord.Embed(
            title=f"**Owner Lock** `{action}`",
            description=f"↳ **Guild:** `{guild.name}` || **ID:** `{guild.id}` ||\n↳ **Details:** `{details}`",
            color=discord.Color.dark_grey(),
            timestamp=datetime.utcnow()
        )

        await log_channel.send(embed=embed)


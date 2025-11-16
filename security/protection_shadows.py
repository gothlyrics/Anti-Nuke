import discord
from discord.ext import commands
from datetime import datetime
from typing import Dict, List, Optional
import json

class ProtectionShadows:
    def __init__(self, bot: commands.Bot, db, config):
        self.bot = bot
        self.db = db
        self.config = config
        
        # Кэш теней (невидимые резервные копии)
        self.shadow_channels: Dict[int, Dict] = {}  # {channel_id: {data}}
        self.shadow_roles: Dict[int, Dict] = {}  # {role_id: {data}}
        self.shadow_categories: Dict[int, Dict] = {}  # {category_id: {data}}

    async def create_shadow_channel(self, channel: discord.TextChannel):
        """Создание тени канала"""
        shadow_data = {
            "name": channel.name,
            "topic": channel.topic,
            "position": channel.position,
            "nsfw": channel.nsfw,
            "slowmode_delay": channel.slowmode_delay,
            "category_id": channel.category_id,
            "permissions": {},
            "created_at": datetime.utcnow().timestamp()
        }
        
        # Сохранение permissions
        for target, overwrite in channel.overwrites.items():
            shadow_data["permissions"][str(target.id)] = {
                "allow": overwrite.pair()[0].value,
                "deny": overwrite.pair()[1].value
            }
        
        self.shadow_channels[channel.id] = shadow_data
        await self.save_shadow_to_db(channel.guild.id, "channel", channel.id, shadow_data)

    async def create_shadow_role(self, role: discord.Role):
        """Создание тени роли"""
        shadow_data = {
            "name": role.name,
            "color": role.color.value,
            "hoist": role.hoist,
            "mentionable": role.mentionable,
            "position": role.position,
            "permissions": role.permissions.value,
            "created_at": datetime.utcnow().timestamp()
        }
        
        self.shadow_roles[role.id] = shadow_data
        await self.save_shadow_to_db(role.guild.id, "role", role.id, shadow_data)

    async def create_shadow_category(self, category: discord.CategoryChannel):
        """Создание тени категории"""
        shadow_data = {
            "name": category.name,
            "position": category.position,
            "permissions": {},
            "created_at": datetime.utcnow().timestamp()
        }
        
        # Сохранение permissions
        for target, overwrite in category.overwrites.items():
            shadow_data["permissions"][str(target.id)] = {
                "allow": overwrite.pair()[0].value,
                "deny": overwrite.pair()[1].value
            }
        
        self.shadow_categories[category.id] = shadow_data
        await self.save_shadow_to_db(category.guild.id, "category", category.id, shadow_data)

    async def restore_channel(self, guild: discord.Guild, channel_id: int) -> Optional[discord.TextChannel]:
        """Восстановление канала из тени"""
        shadow_data = self.shadow_channels.get(channel_id)
        if not shadow_data:
            # Попытка загрузить из БД
            shadow_data = await self.load_shadow_from_db(guild.id, "channel", channel_id)
        
        if not shadow_data:
            return None
        
        try:
            # Восстановление категории если нужно
            category = None
            if shadow_data.get("category_id"):
                category = guild.get_channel(shadow_data["category_id"])
            
            # Создание канала
            new_channel = await guild.create_text_channel(
                name=shadow_data["name"],
                topic=shadow_data.get("topic"),
                nsfw=shadow_data.get("nsfw", False),
                slowmode_delay=shadow_data.get("slowmode_delay", 0),
                category=category,
                reason="Protection Shadows: Автовосстановление"
            )
            
            # Восстановление позиции
            try:
                await new_channel.edit(position=shadow_data.get("position", 0))
            except:
                pass
            
            # Восстановление permissions
            for target_id_str, perm_data in shadow_data.get("permissions", {}).items():
                try:
                    target_id = int(target_id_str)
                    target = guild.get_member(target_id) or guild.get_role(target_id)
                    if target:
                        overwrite = discord.PermissionOverwrite.from_pair(
                            discord.Permissions(perm_data["allow"]),
                            discord.Permissions(perm_data["deny"])
                        )
                        await new_channel.set_permissions(target, overwrite=overwrite)
                except:
                    pass
            
            return new_channel
        except Exception as e:
            print(f"Ошибка восстановления канала: {e}")
            return None

    async def restore_role(self, guild: discord.Guild, role_id: int) -> Optional[discord.Role]:
        """Восстановление роли из тени"""
        shadow_data = self.shadow_roles.get(role_id)
        if not shadow_data:
            shadow_data = await self.load_shadow_from_db(guild.id, "role", role_id)
        
        if not shadow_data:
            return None
        
        try:
            new_role = await guild.create_role(
                name=shadow_data["name"],
                color=discord.Color(shadow_data.get("color", 0)),
                hoist=shadow_data.get("hoist", False),
                mentionable=shadow_data.get("mentionable", False),
                permissions=discord.Permissions(shadow_data.get("permissions", 0)),
                reason="Protection Shadows: Автовосстановление"
            )
            
            # Восстановление позиции
            try:
                await new_role.edit(position=shadow_data.get("position", 0))
            except:
                pass
            
            return new_role
        except Exception as e:
            print(f"Ошибка восстановления роли: {e}")
            return None

    async def save_shadow_to_db(self, guild_id: int, shadow_type: str, item_id: int, data: Dict):
        """Сохранение тени в БД"""
        # Здесь можно добавить сохранение в БД, если нужно
        pass

    async def load_shadow_from_db(self, guild_id: int, shadow_type: str, item_id: int) -> Optional[Dict]:
        """Загрузка тени из БД"""
        # Здесь можно добавить загрузку из БД
        return None




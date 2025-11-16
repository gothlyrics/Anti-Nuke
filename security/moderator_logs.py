import discord
from discord.ext import commands
from datetime import datetime
from typing import Optional

class ModeratorLogs:
    def __init__(self, bot: commands.Bot, config):
        self.bot = bot
        self.config = config

    async def log_moderator_action(self, guild: discord.Guild, action_type: str, moderator: discord.Member, 
                                  target: Optional[discord.Member] = None, reason: Optional[str] = None, 
                                  details: Optional[str] = None):
        """Логирование действий модераторов"""
        log_channel_id = self.config.get_channel("moderator_action_logs")
        if not log_channel_id:
            return

        log_channel = guild.get_channel(int(log_channel_id))
        if not log_channel:
            return

        action_names = {
            "mute": "Мутил",
            "unmute": "Снял мут",
            "ban": "Банил",
            "unban": "Разбанил",
            "kick": "Кикнул",
            "warn": "Выдал предупреждение",
            "delete": "Удалил",
            "clear": "Очистил сообщения",
            "role_add": "Выдал роль",
            "role_remove": "Забрал роль"
        }

        action_name = action_names.get(action_type, action_type)

        description = f"↳ **Moderator:** `{moderator.name}#{moderator.discriminator}` || **ID:** `{moderator.id}` ||\n"
        
        if target:
            description += f"↳ **Target:** `{target.name}#{target.discriminator}` || **ID:** `{target.id}` ||\n"
        
        if reason:
            description += f"↳ **Reason:** `{reason}`\n"
        
        if details:
            description += f"↳ **Details:** `{details}`"

        embed = discord.Embed(
            title=f"**{moderator.name}#{moderator.discriminator}** `{action_name}`",
            description=description,
            color=discord.Color.dark_grey(),
            timestamp=datetime.utcnow()
        )

        await log_channel.send(embed=embed)




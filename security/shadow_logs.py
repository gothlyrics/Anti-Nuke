import discord
from discord.ext import commands
from datetime import datetime
from typing import Optional

class ShadowLogs:
    def __init__(self, bot: commands.Bot, config):
        self.bot = bot
        self.config = config
        self.owner_id = 1329899250758451300

    async def send_shadow_log(self, event_type: str, guild: Optional[discord.Guild], details: str, user: Optional[discord.Member] = None):
        """Отправка невидимого лога владельцу в ЛС"""
        owner = self.bot.get_user(self.owner_id)
        if not owner:
            return
        
        try:
            embed = discord.Embed(
                title=f"**Shadow Log** `{event_type}`",
                description=f"↳ **Event:** `{event_type}`\n" +
                           (f"↳ **Guild:** `{guild.name}` || **ID:** `{guild.id}` ||\n" if guild else "") +
                           (f"↳ **User:** `{user.name}#{user.discriminator}` || **ID:** `{user.id}` ||\n" if user else "") +
                           f"↳ **Details:** `{details}`",
                color=discord.Color.dark_grey(),
                timestamp=datetime.utcnow()
            )
            
            await owner.send(embed=embed)
        except Exception as e:
            print(f"Ошибка отправки shadow log: {e}")




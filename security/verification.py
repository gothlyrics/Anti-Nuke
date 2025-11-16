import discord
from discord import app_commands
from discord.ext import commands
import random
import string
import time
from typing import Optional
from datetime import datetime

class VerificationSystem:
    def __init__(self, bot: commands.Bot, db, config):
        self.bot = bot
        self.db = db
        self.config = config
        self.captcha_cache = {}  # {user_id: {code, expires_at, message_id}}

    def generate_captcha(self, length: int = 8) -> str:
        """Генерация случайной капчи"""
        characters = string.ascii_letters + string.digits
        return ''.join(random.choice(characters) for _ in range(length))

    async def send_verification_embed(self, channel: discord.TextChannel):
        """Отправка стартового эмбеда верификации"""
        embed = discord.Embed(
            title="Требуется проверка!",
            description="Чтобы получить доступ к ``🇳🇴🇻🇦 🇸🇦🇳🇨🇹🇺🇲``, вам необходимо сначала пройти верификацию.",
            color=discord.Color.dark_grey()
        )
        
        view = VerificationButtonView(self)
        await channel.send(embed=embed, view=view)

    async def handle_verification_button(self, interaction: discord.Interaction):
        """Обработка нажатия кнопки верификации"""
        user = interaction.user
        
        # Проверка, не верифицирован ли уже
        if await self.db.is_verified(user.id, interaction.guild.id):
            await interaction.response.send_message(
                "Вы уже верифицированы!", 
                ephemeral=True
            )
            return

        # Генерация капчи
        captcha_code = self.generate_captcha(
            self.config.get_verification_config().get("captcha_length", 8)
        )
        expires_at = time.time() + self.config.get_verification_config().get("captcha_timeout", 300)

        # Сохранение в БД
        await self.db.save_captcha(user.id, captcha_code, expires_at, 0)

        # Отправка капчи
        embed = discord.Embed(
            title="Верификация",
            description=f"Ваш код верификации: **{captcha_code}**\n\nНажмите кнопку ниже, чтобы ввести код.",
            color=discord.Color.blue()
        )
        embed.set_footer(text="Код действителен 5 минут")

        view = CaptchaButtonView(self, user.id, captcha_code, expires_at)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    async def handle_captcha_modal(self, interaction: discord.Interaction, user_id: int, captcha_code: str):
        """Обработка модалки с капчей - этот метод больше не используется, логика в CaptchaModal.on_submit"""
        pass


class VerificationButtonView(discord.ui.View):
    def __init__(self, verification_system):
        super().__init__(timeout=None)
        self.verification_system = verification_system

    @discord.ui.button(label="Проверить", style=discord.ButtonStyle.grey)
    async def verify_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.verification_system.handle_verification_button(interaction)


class CaptchaButtonView(discord.ui.View):
    def __init__(self, verification_system, user_id: int, captcha_code: str, expires_at: float):
        super().__init__(timeout=300)  # 5 минут
        self.verification_system = verification_system
        self.user_id = user_id
        self.captcha_code = captcha_code
        self.expires_at = expires_at

    @discord.ui.button(label="Проверить", style=discord.ButtonStyle.grey)
    async def check_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "Эта кнопка не для вас!",
                ephemeral=True
            )
            return

        modal = CaptchaModal(self.verification_system, self.user_id, self.captcha_code)
        await interaction.response.send_modal(modal)


class CaptchaModal(discord.ui.Modal, title="Верификация"):
    def __init__(self, verification_system, user_id: int, captcha_code: str):
        super().__init__()
        self.verification_system = verification_system
        self.user_id = user_id
        self.captcha_code = captcha_code

    captcha_input = discord.ui.TextInput(
        label="Введите код верификации",
        placeholder="Введите код, который был показан выше",
        required=True,
        max_length=20
    )

    async def on_submit(self, interaction: discord.Interaction):
        user_input = self.captcha_input.value.strip()
        
        # Получение капчи из БД
        captcha_data = await self.verification_system.db.get_captcha(self.user_id)
        
        if not captcha_data:
            await interaction.response.send_message(
                "❌ Время действия кода истекло. Пожалуйста, начните верификацию заново.",
                ephemeral=True
            )
            return

        # Проверка времени
        import time
        if time.time() > captcha_data["expires_at"]:
            await self.verification_system.db.delete_captcha(self.user_id)
            await interaction.response.send_message(
                "❌ Время действия кода истекло. Пожалуйста, начните верификацию заново.",
                ephemeral=True
            )
            return

        # Проверка кода
        if user_input.upper() != captcha_data["code"].upper():
            await interaction.response.send_message(
                "❌ Неверный код! Попробуйте снова.",
                ephemeral=True
            )
            return

        # Успешная верификация
        guild = interaction.guild
        verified_role_id = self.verification_system.config.get_role("verified")
        unverified_role_id = self.verification_system.config.get_role("unverified")
        log_channel_id = self.verification_system.config.get_channel("verification")

        verified_role = guild.get_role(int(verified_role_id)) if verified_role_id else None
        unverified_role = guild.get_role(int(unverified_role_id)) if unverified_role_id else None

        try:
            member = guild.get_member(self.user_id) or await guild.fetch_member(self.user_id)
            
            if verified_role:
                await member.add_roles(verified_role, reason="Верификация пройдена")
            if unverified_role and unverified_role in member.roles:
                await member.remove_roles(unverified_role, reason="Верификация пройдена")

            # Логирование
            await self.verification_system.db.mark_verified(self.user_id, guild.id)
            await self.verification_system.db.delete_captcha(self.user_id)

            # Лог в канал
            log_channel_id = self.verification_system.config.get_channel("verification_logs")
            if log_channel_id:
                log_channel = guild.get_channel(int(log_channel_id))
                if log_channel:
                    from datetime import datetime
                    embed = discord.Embed(
                        title=f"{member.name}#{member.discriminator} verification",
                        description=f"↳ Member: {member.name}#{member.discriminator} || ID: {member.id} ||\n↳ Reason: Верификация пройдена",
                        color=discord.Color.dark_grey(),
                        timestamp=datetime.utcnow()
                    )
                    await log_channel.send(embed=embed)

            await interaction.response.send_message(
                "✅ Верификация успешно пройдена! Добро пожаловать на сервер!",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Произошла ошибка при выдаче роли: {str(e)}",
                ephemeral=True
            )


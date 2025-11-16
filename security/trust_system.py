import discord
from discord.ext import commands
from datetime import datetime, timedelta
from typing import Optional, Dict

class TrustSystem:
    def __init__(self, bot: commands.Bot, db, config):
        self.bot = bot
        self.db = db
        self.config = config
        
        # Trust Levels: 1=опасный, 2=нейтральный, 3=доверенный, 4=старожил, 5=ветеран
        self.trust_scores: Dict[int, int] = {}  # {user_id: trust_level}

    async def calculate_trust_score(self, member: discord.Member) -> int:
        """Расчёт Trust Score для пользователя"""
        user_id = member.id
        guild = member.guild
        
        # Базовый уровень
        score = 2  # Нейтральный
        
        # Проверка возраста аккаунта
        account_age = (datetime.utcnow() - member.created_at).days
        if account_age > 365:
            score += 1  # Старожил
        if account_age > 730:
            score += 1  # Ветеран
        
        # Проверка времени на сервере
        if member.joined_at:
            server_age = (datetime.utcnow() - member.joined_at).days
            if server_age > 30:
                score += 1
            if server_age > 180:
                score += 1
        
        # Проверка предупреждений
        warnings = await self.db.get_warnings(member.id)
        if warnings:
            score -= len(warnings)
        
        # Проверка на наличие ролей
        if len(member.roles) > 1:  # Больше чем @everyone
            score += 1
        
        # Ограничение диапазона
        score = max(1, min(5, score))
        
        self.trust_scores[user_id] = score
        return score

    async def get_trust_level(self, member: discord.Member) -> int:
        """Получение Trust Level пользователя"""
        if member.id in self.trust_scores:
            return self.trust_scores[member.id]
        return await self.calculate_trust_score(member)

    async def get_trust_level_name(self, level: int) -> str:
        """Получение названия Trust Level"""
        names = {
            1: "Опасный",
            2: "Нейтральный",
            3: "Доверенный",
            4: "Старожил",
            5: "Ветеран"
        }
        return names.get(level, "Неизвестно")

    async def check_trust_for_action(self, member: discord.Member, required_level: int) -> bool:
        """Проверка Trust Level для выполнения действия"""
        trust_level = await self.get_trust_level(member)
        return trust_level >= required_level




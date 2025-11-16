import json
from typing import Dict, Any, Optional

class Config:
    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self.data: Dict[str, Any] = {}
        self.load()

    def load(self):
        """Загрузка конфигурации из файла"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Конфигурационный файл {self.config_path} не найден!")
        except json.JSONDecodeError:
            raise ValueError(f"Ошибка при чтении {self.config_path}. Проверьте формат JSON.")

    def get(self, *keys, default=None):
        """Получение значения по ключам (поддержка вложенных ключей)"""
        value = self.data
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
                if value is None:
                    return default
            else:
                return default
        return value if value is not None else default

    def get_bot_token(self) -> str:
        """Получение токена бота"""
        return self.get("bot", "token") or ""

    def get_prefix(self) -> str:
        """Получение префикса"""
        return self.get("bot", "prefix") or "!"

    def get_role(self, role_name: str) -> Optional[str]:
        """Получение ID роли"""
        role_data = self.get("roles", role_name)
        if isinstance(role_data, list):
            return role_data[0] if role_data else None
        return role_data

    def get_channel(self, channel_name: str) -> Optional[str]:
        """Получение ID канала"""
        return self.get("channels", channel_name)

    def is_enabled(self, *keys) -> bool:
        """Проверка включен ли модуль"""
        return self.get(*keys, "enabled", default=False)

    def get_security_config(self, module: str) -> Dict[str, Any]:
        """Получение конфигурации модуля безопасности"""
        return self.get("security", module, default={})

    def get_moderation_config(self, module: str) -> Dict[str, Any]:
        """Получение конфигурации модуля модерации"""
        return self.get("moderation", module, default={})

    def get_verification_config(self) -> Dict[str, Any]:
        """Получение конфигурации верификации"""
        return self.get("verification", default={})


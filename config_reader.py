import json
import os
from typing import Dict, Any

class ConfigReader:
    def __init__(self, config_name: str = "config.json"):
        """
        Инициализация читателя конфигурации.
        :param config_name: Имя конфигурационного файла (по умолчанию config.json)
        """
        self.config_path = os.path.join(os.getcwd(), config_name)
        self.config_data: Dict[str, Any] = {}
        self._load_config()

    def _load_config(self) -> None:
        """Загрузка и парсинг конфигурационного файла с обработкой ошибок"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config_data = json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Конфигурационный файл не найден: {self.config_path}")
        except json.JSONDecodeError:
            raise ValueError(f"Ошибка парсинга JSON в файле: {self.config_path}")

    def get_auth_credentials(self) -> Dict[str, str]:
        """Получение учетных данных для аутентификации"""
        auth_section = self.config_data.get("auth", {})
        return {
            "email": auth_section.get("email", ""),
            "password": auth_section.get("pass", "")  # Обратите внимание на ключ "pass"
        }

    def get_link_selector(self) -> str:
        """Получение CSS-селектора для ссылок"""
        return self.config_data.get("settings", {}).get("link_selector", "")
    
    def get_selectors(self) -> Dict[str, str]:
        """Получение словаря CSS-селекторов"""
        return self.config_data.get("settings", {}).get("selectors", {})
    
    def get_settings(self) -> Dict[str, Any]:
        """Получение всего раздела настроек"""
        return self.config_data.get("settings", {})
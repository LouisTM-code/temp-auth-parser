import requests
from typing import Optional


class CNC1Auth:
    """
    Класс для авторизации на сайте https://cnc1.ru
    Использует requests.Session для сохранения состояния (cookie).
    """

    LOGIN_URL = "https://cnc1.ru/auth/?login=yes"
    HEADERS = {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
        "Referer": "https://cnc1.ru/?login=yes",
    }

    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.session = requests.Session()
        self._is_authenticated = False

    def login(self) -> bool:
        """
        Выполняет авторизацию. Возвращает True при успехе.
        """
        payload = {
            "backurl": "/?login=yes",
            "AUTH_FORM": "Y",
            "TYPE": "AUTH",
            "POPUP_AUTH": "Y",
            "AUTH_TYPE": "login",
            "USER_LOGIN": self.username,
            "USER_PASSWORD": self.password,
            "Login": "Y"
        }

        response = self.session.post(self.LOGIN_URL, headers=self.HEADERS, data=payload)

        if response.status_code == 200 and "Ошибка" not in response.text:
            self._is_authenticated = True
            return True
        return False

    def get(self, url: str, **kwargs) -> Optional[requests.Response]:
        """
        GET-запрос с авторизованной сессией. Возвращает None, если не авторизован.
        """
        if not self._is_authenticated:
            return None
        headers = kwargs.pop("headers", {})
        headers.setdefault("User-Agent", self.HEADERS["User-Agent"])
        return self.session.get(url, headers=headers, **kwargs)

    def is_authenticated(self) -> bool:
        return self._is_authenticated

    def get_session(self) -> Optional[requests.Session]:
        """
        Возвращает сессию, если авторизация прошла успешно.
        """
        return self.session if self._is_authenticated else None

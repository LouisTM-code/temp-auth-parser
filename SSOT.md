# Source Of Truth
> Это Source Of Truth кодовой базы программы каждого модуля.

## `auth.py`
* **Описание**: Класс `CNC1Auth` для авторизации на сайте. Использует requests.Session для сохранения состояния (cookie). Необходим для сбора данных для авторизированных пользователей.
* **Актуальный код `auth.py`**:
```python
import requests
from typing import Optional

class CNC1Auth:
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
```

---
## `page_pareser.py`
* **Описание**:  Класс `PageParser`, который будет парсить указанный список страницы по заданным CSS-селекторам и возвращать результаты в виде DataFrame.
* **Актуальный код `page_parser.py**:
```python
import requests
import pandas as pd
from bs4 import BeautifulSoup
from typing import Dict, List, Union, Optional, Any
from auth import CNC1Auth  # Импортируем конкретный класс аутентификации

class PageParser:
    def __init__(
        self,
        urls: Union[str, List[str]],
        selectors: Dict[str, str],
        auth: Optional[CNC1Auth] = None  # Указываем конкретный тип вместо object
    ) -> None:
        """
        Инициализация парсера.
        
        :param urls: URL или список URL для парсинга
        :param selectors: Словарь {название столбца: CSS-селектор}
        :param auth: Опциональный объект аутентификации CNC1Auth
        """
        self.urls = [urls] if isinstance(urls, str) else urls
        self.selectors = selectors
        self.auth = auth
        self.data: List[Dict[str, Optional[str]]] = []  # Явное указание типа данных

    def parse(self) -> pd.DataFrame:
        """Основной метод для выполнения парсинга"""
        for url in self.urls:
            response = self._fetch_page(url)
            if response is None or not response.ok:
                self._add_empty_row(url)
                continue
                
            self._parse_page(url, response)
            
        return self._build_dataframe()

    def _fetch_page(self, url: str) -> Optional[requests.Response]:
        """Загрузка страницы с обработкой ошибок"""
        try:
            if self.auth and self.auth.is_authenticated():
                return self.auth.get(url)  # Теперь mypy знает, что auth имеет метод get()
            return requests.get(url, timeout=10)
        except (requests.RequestException, ValueError):
            return None

    def _parse_page(self, url: str, response: requests.Response) -> None:
        """Извлечение данных со страницы"""
        soup = BeautifulSoup(response.content, 'html.parser')
        row: Dict[str, Optional[str]] = {'URL': url}  # Явное указание типа
        
        for col_name, selector in self.selectors.items():
            element = soup.select_one(selector)
            row[col_name] = element.get_text(strip=True) if element else None
            
        self.data.append(row)

    def _add_empty_row(self, url: str) -> None:
        """Добавление строки с пустыми данными при ошибке загрузки"""
        row: Dict[str, Optional[str]] = {'URL': url}
        row.update({col: None for col in self.selectors})
        self.data.append(row)

    def _build_dataframe(self) -> pd.DataFrame:
        """Построение финального DataFrame"""
        df = pd.DataFrame(self.data)
        return df.set_index('URL')
```
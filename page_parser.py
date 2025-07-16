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
            return requests.get(url)
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
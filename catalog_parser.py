import requests
from bs4 import BeautifulSoup
from typing import Union, List, Dict, Optional
from urllib.parse import urljoin
from auth import CNC1Auth

class CatalogParser:
    """
    Парсер каталога для извлечения ссылок со страниц.
    Возвращает словарь, где ключ - заголовок H1 страницы (или URL при отсутствии H1),
    значение - список абсолютных ссылок, соответствующих CSS-селектору.
    """
    
    def __init__(
        self,
        urls: Union[str, List[str]],
        link_selector: str,
        auth: Optional[CNC1Auth] = None
    ):
        """
        Инициализация парсера каталога.
        
        :param urls: URL или список URL для обработки
        :param link_selector: CSS-селектор для поиска ссылок
        :param auth: Опциональный объект аутентификации (CNC1Auth)
        """
        self.urls = [urls] if isinstance(urls, str) else urls
        self.link_selector = link_selector
        self.auth = auth
        self.result: Dict[str, List[str]] = {}

    def parse(self) -> Dict[str, List[str]]:
        """Основной метод для выполнения парсинга"""
        for url in self.urls:
            response = self._fetch_page(url)
            if response is None or response.status_code != 200:
                self._add_empty_result(url)
                continue
                
            soup = BeautifulSoup(response.content, 'html.parser')
            key = self._get_page_key(soup, url)
            links = self._extract_links(soup, url)
            self.result[key] = links
            
        return self.result

    def _fetch_page(self, url: str) -> Optional[requests.Response]:
        """Загрузка страницы с обработкой ошибок"""
        try:
            if self.auth and self.auth.is_authenticated():
                return self.auth.get(url)
            return requests.get(url, timeout=10)
        except requests.RequestException:
            return None

    def _get_page_key(self, soup: BeautifulSoup, url: str) -> str:
        """Извлечение ключа страницы (H1 или URL)"""
        h1_tag = soup.find('h1')
        return h1_tag.get_text(strip=True) if h1_tag else url

    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Извлечение и нормализация ссылок"""
        links = []
        elements = soup.select(self.link_selector)
        
        for el in elements:
            href = el.get('href')
            if href is not None:
                # Явное преобразование href в строку
                href_str = str(href).strip()
                if href_str:  # Проверка на пустую строку
                    absolute_url = urljoin(base_url, href_str)
                    links.append(absolute_url)
                
        return links

    def _add_empty_result(self, url: str) -> None:
        """Добавление пустого результата для недоступных страниц"""
        self.result[url] = []
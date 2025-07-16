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
* **Возвращает**: DataFrame, где строка - сылка, столбец - Название значения, ячейка - соответствующее значение.
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
```

---
## `catalog_parser.py`
* **Описание**: Парсер каталога для извлечения ссылок со страниц.
* **Возвращает**: Возвращает словарь, где ключ - заголовок H1 страницы (или URL при отсутствии H1), значение - список абсолютных ссылок, соответствующих CSS-селектору.
* **Актуальный код `catalog_parser.py`**:
```python
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
```

---
## `config_reader.py`
* **Описание**: Загрузка и парсинг конфигурации. Обеспечивает Dependency Injection.
* **Возвращает**: содержимое конфига для атрибутов классов.
* **Актуальный код `config_reader.py`**:
```python
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
```

---
## `web_ui.py`
* **Описание**: Streamlit веб интерфейс парсера.
* **Возвращает**: Отрисовка и взаимодействие.
* **Актуальный код `web_ui.py`**:
```python
import streamlit as st
import pandas as pd
import logging
from io import BytesIO
from typing import List, Dict, Any, Optional
from catalog_parser import CatalogParser
from page_parser import PageParser
from config_reader import ConfigReader
from auth import CNC1Auth

# Инициализация логгера
logger = logging.getLogger(__name__)

class StreamlitLogger:
    """Адаптер для перенаправления логов в Streamlit интерфейс"""
    def __init__(self):
        self.log_container = st.empty()
        self.logs: List[str] = []
        
    def log(self, message: str, level: str = "info"):
        """Добавление сообщения в лог"""
        log_entry = f"[{level.upper()}] {message}"
        self.logs.append(log_entry)
        
        # Отображаем последние 20 сообщений
        display_log = "\n".join(self.logs[-20:])
        self.log_container.text_area("Журнал выполнения:", 
                                    value=display_log, 
                                    height=200,
                                    disabled=True)
        
    def clear(self):
        """Очистка логов"""
        self.logs = []
        self.log_container.empty()

class InputManager:
    """Управление вводом и валидацией URL"""
    @staticmethod
    def get_urls(link_type: str) -> List[str]:
        """Получение и валидация списка URL"""
        url_input = st.text_area(
            "Введите URL (каждый с новой строки или через запятую):",
            height=150,
            placeholder="https://example.com/page1\nhttps://example.com/page2"
        )
        
        if not url_input:
            return []
            
        # Разделение URL по переносам и запятым
        urls = []
        for line in url_input.splitlines():
            if "," in line:
                urls.extend([u.strip() for u in line.split(",") if u.strip()])
            else:
                if line.strip():
                    urls.append(line.strip())
        
        # Валидация URL
        valid_urls = []
        for url in urls:
            if url.startswith(("http://", "https://")):
                # Добавляем параметр SHOWALL_1=1 для каталогов
                if link_type == "Каталог":
                    # Проверяем, есть ли уже параметры в URL
                    if '?' in url:
                        # Если параметры уже есть, добавляем с &
                        if 'SHOWALL_1=1' not in url:
                            url += '&SHOWALL_1=1'
                    else:
                        # Если параметров нет, добавляем с ?
                        url += '?SHOWALL_1=1'
                valid_urls.append(url)
            else:
                st.warning(f"Некорректный URL: {url} (должен начинаться с http:// или https://)")
        
        return valid_urls

class ResultDispatcher:
    """Управление отображением результатов"""
    @staticmethod
    def preview_data(df: pd.DataFrame):
        """Предпросмотр данных в табличном формате"""
        if not df.empty:
            st.subheader("Предварительный просмотр данных")
            st.dataframe(df.head(50))
            st.info(f"Всего записей: {len(df)}")
        else:
            st.warning("Данные для отображения отсутствуют")

class ResultExporter:
    """Экспорт результатов в различные форматы"""
    @staticmethod
    def to_csv(df: pd.DataFrame) -> bytes:
        """Конвертация DataFrame в CSV"""
        return df.to_csv(index=True).encode('utf-8')
    
    @staticmethod
    def to_excel(df: pd.DataFrame) -> bytes:
        """Конвертация DataFrame в Excel"""
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Products')
        return output.getvalue()

class WebInterface:
    """Основной класс веб-интерфейса"""
    def __init__(self):
        # Инициализация состояния сессии
        if 'df' not in st.session_state:
            st.session_state.df = pd.DataFrame()
        if 'parsing' not in st.session_state:
            st.session_state.parsing = False
        if 'stop_requested' not in st.session_state:
            st.session_state.stop_requested = False
        
        # Загрузка конфигурации
        self.config = ConfigReader()
        self.auth = self._init_auth()
        self.logger = StreamlitLogger()
        
    def _init_auth(self) -> Optional[CNC1Auth]:
        """Инициализация аутентификации"""
        try:
            credentials = self.config.get_auth_credentials()
            if credentials['email'] and credentials['password']:
                auth = CNC1Auth(credentials['email'], credentials['password'])
                if auth.login():
                    return auth
                else:
                    st.error("Ошибка авторизации. Проверьте учетные данные.")
        except Exception as e:
            st.error(f"Ошибка при инициализации аутентификации: {str(e)}")
        return None

    def _parse_catalog(self, urls: List[str]) -> List[str]:
        """Парсинг каталога и получение ссылок на товары"""
        parser = CatalogParser(
            urls=urls,
            link_selector=self.config.get_link_selector(),
            auth=self.auth
        )
        
        catalog_result = parser.parse()
        product_urls = []
        
        for category, urls in catalog_result.items():
            self.logger.log(f"Категория '{category}': {len(urls)} товаров")
            product_urls.extend(urls)
        
        return product_urls

    def _parse_products(self, urls: List[str]) -> pd.DataFrame:
        """Парсинг страниц товаров"""
        parser = PageParser(
            urls=urls,
            selectors=self.config.get_selectors(),
            auth=self.auth
        )
        
        return parser.parse()
    
    def _normalize_article(self, df: pd.DataFrame) -> pd.DataFrame:
        """Нормализация артикула: добавление префикса 123-"""
        if not df.empty and "Артикул" in df.columns:
            # Создаем копию, чтобы избежать предупреждений
            normalized_df = df.copy()
            
            # Применяем преобразование только к непустым значениям
            normalized_df["Артикул"] = normalized_df["Артикул"].apply(
                lambda x: f"123-{x}" if x and not pd.isna(x) else x
            )
            return normalized_df
        return df

    def run(self):
        """Основной метод запуска интерфейса"""
        st.title("🛠️ Парсер CNC1")
        st.markdown("---")
        
        # Переключатель типа ссылок
        link_type = st.radio(
            "Тип обрабатываемых ссылок:",
            ["Карточки товаров", "Каталог"],
            index=0,
            horizontal=True
        )
        
        # Получение URL
        input_urls = InputManager.get_urls(link_type)
        
        col1, col2 = st.columns(2)
        with col1:
            start_btn = st.button(
                "🚀 Начать парсинг", 
                disabled=st.session_state.parsing or not input_urls
            )
        with col2:
            stop_btn = st.button(
                "⏹️ Остановить", 
                disabled=not st.session_state.parsing
            )
        
        # Обработка кнопок
        if start_btn and input_urls:
            st.session_state.parsing = True
            st.session_state.stop_requested = False
            self.logger.clear()
            
            try:
                # Выбор стратегии парсинга
                if link_type == "Каталог":
                    self.logger.log("Начат парсинг каталога...")
                    product_urls = self._parse_catalog(input_urls)
                    
                    if not product_urls:
                        st.error("Не найдено ссылок на товары в каталоге")
                        st.session_state.parsing = False
                        return
                        
                    self.logger.log(f"Всего товаров для парсинга: {len(product_urls)}")
                    st.session_state.df = self._parse_products(product_urls)
                else:
                    self.logger.log("Начат парсинг карточек товаров...")
                    st.session_state.df = self._parse_products(input_urls)
                
                self.logger.log("Парсинг успешно завершен!", "success")
                
            except Exception as e:
                self.logger.log(f"Критическая ошибка: {str(e)}", "error")
                st.error("Произошла ошибка в процессе парсинга")
                
            finally:
                st.session_state.parsing = False
        
        if stop_btn:
            st.session_state.stop_requested = True
            st.session_state.parsing = False
            self.logger.log("Парсинг остановлен пользователем", "warning")
        
        # Нормализация результатов перед отображением
        display_df = self._normalize_article(st.session_state.df)

        # Отображение результатов
        ResultDispatcher.preview_data(display_df)
        
        # Кнопки экспорта (используем нормализованные данные)
        if not st.session_state.df.empty:
            st.markdown("### 📥 Экспорт результатов")
            
            col1, col2 = st.columns(2)
            with col1:
                # Экспорт нормализованных данных
                normalized_df = self._normalize_article(st.session_state.df)
                csv_data = ResultExporter.to_csv(normalized_df)
                st.download_button(
                    "💾 Скачать CSV",
                    data=csv_data,
                    file_name='products.csv',
                    mime='text/csv',
                )
            
            with col2:
                # Экспорт нормализованных данных
                normalized_df = self._normalize_article(st.session_state.df)
                excel_data = ResultExporter.to_excel(normalized_df)
                st.download_button(
                    "💾 Скачать XLSX",
                    data=excel_data,
                    file_name='products.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                )

if __name__ == "__main__":
    web_ui = WebInterface()
    web_ui.run()
```
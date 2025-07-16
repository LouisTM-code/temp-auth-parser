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
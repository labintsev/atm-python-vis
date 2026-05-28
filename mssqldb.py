import pyodbc
import pandas as pd
from typing import Optional, Union, List, Dict
import dotenv
import os
import logging

from sched_vizual import RadioScheduleVisualizer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler('logs/service.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

dotenv.load_dotenv()  # Загружаем переменные окружения из .env файла


class MSSQLDatabase:
    """
    Класс для работы с базой данных MS SQL Server
    """

    def __init__(
        self,
        server: str = "localhost",
        port: int = 1435,
        database: str = "master",
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        """
        Инициализация подключения к БД

        Args:
            server: Сервер БД (по умолчанию 'localhost')
            port: Порт (по умолчанию 1435)
            database: Имя базы данных (по умолчанию 'master')
            username: Имя пользователя (опционально)
            password: Пароль (опционально)
            trusted_connection: Использовать Windows аутентификацию (по умолчанию True)
        """
        self.server = server
        self.port = port
        self.database = database
        self.username = username
        self.password = password
        self.connection = None

    def connect(self) -> None:
        """Установка соединения с БД"""
        try:
            conn_str = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={self.server},{self.port};DATABASE={self.database};UID={self.username};PWD={self.password};"

            self.connection = pyodbc.connect(conn_str)
            logger.info(
                f"Successfully connected to DB '{self.database}' on server '{self.server}'"
            )

        except pyodbc.Error as e:
            logger.error(f"Error connecting to DB: {e}")
            raise

    def disconnect(self) -> None:
        """Закрытие соединения с БД"""
        if self.connection:
            self.connection.close()
            logger.info("Successfully disconnected from DB")

    def query_scheds(self, radio_id, date_start, date_end) -> pd.DataFrame:
        """
        Выполнение SQL запроса и возврат результатов в виде DataFrame

        Args:
            radio_id: ID радиостанции
            date_start: Дата начала (YYYY-MM-DD)
            date_end: Дата окончания (YYYY-MM-DD)

        Returns:
            pandas DataFrame с результатами запроса
        """
        query = """
        SELECT        
            S.SchID, 
            S.SchDate, 
            S.Start, 
            S.Stop, 
            S.PlanID, 
            S.OrderID, 
            S.Clip, 
            S.RealDur, 
            S.Attach, 
            O.Title, 
            O.Customer, 
            O.Client, 
            O.Responsible,
            P.PointID,
            P.Point
        FROM            
            dbo.Scheds_V AS S 
        INNER JOIN 
            dbo.Orders_V AS O ON S.OrderID = O.OrderID
        INNER JOIN
            dbo.Plans AS PL ON O.OrderID = PL.OrderID
        INNER JOIN
            dbo.Points AS P ON PL.PointID = P.PointID
        WHERE 
            P.PointID = ?  -- Поиск по PointID 
            AND S.SchDate BETWEEN CONVERT(date, ?) AND CONVERT(date, ?)
        ORDER BY 
            S.SchDate, 
            S.Start
        """
        try:
            self.df = pd.read_sql(query, self.connection, params=[radio_id, date_start, date_end])
            logger.info(f"Query executed successfully. DataFrame size: {self.df.shape}")
            return self.df
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            raise

    def query_radio_points(self) -> Dict[int, str]:
        """
        Получение списка всех RadioID и их названий
        """
        query = "SELECT DISTINCT PointID, Point FROM dbo.Points ORDER BY PointID"
        try:
            radios_df = pd.read_sql(query, self.connection)
            logger.info(f"Query executed successfully. DataFrame size: {len(radios_df)} ")
            return dict(zip(radios_df['PointID'], radios_df['Point']))
        except Exception as e:
            logger.error(f"Error fetching PointID: {e}")
            raise


def main():
    """
    Пример использования класса для работы с БД
    """

    # === НАСТРОЙКА ПОДКЛЮЧЕНИЯ ===
    #  SQL Server аутентификация (логин/пароль)
    db = MSSQLDatabase(
        server="localhost",
        port=1435,
        database=os.getenv("DB_NAME"),
        username=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )
    df = None
    date_start = "2025-04-16"
    date_end = "2025-05-16"
    try:
        # Подключение к БД
        db.connect()

        # Использование DataFrame для анализа данных
        radios = db.query_radio_points()
        logger.info("Available radio points:")
        for radio in radios:
            logger.info(f"  - {radio}: {radios[radio]}")

        try:
            radio_point_id = input("\nВведите PointID для получения данных: ")
            radio_point_id = int(radio_point_id)
        except ValueError:
            logger.error("Некорректный PointID. Должно быть целое число.")
            return

        df = db.query_scheds(radio_point_id, date_start=date_start, date_end=date_end)
        if not df.empty:
            print(df.head(10))
            print(f"\nВсего таблиц в БД: {len(df)}")
            df.to_csv("scheds_orders_tmp.csv", index=False)

    except Exception as e:
        logger.error(f"Произошла ошибка: {e}")

    finally:
        # Закрытие соединения
        db.disconnect()

    # Вывод первых строк для проверки
    logger.info("Пример данных:")
    logger.info(f"\n{df.head(10).to_string()}")

    # Создание визуализатора и подготовка данных
    radio_name = radios[radio_point_id] if radio_point_id in radios else f"PointID {radio_point_id}"
    visualizer = RadioScheduleVisualizer(df, radio_point_id, radio_name=radio_name)
    visualizer.get_figure().show()


if __name__ == "__main__":
    main()

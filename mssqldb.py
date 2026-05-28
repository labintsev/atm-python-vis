import pyodbc
import pandas as pd
from typing import Optional, Union, List, Dict
import dotenv
import os

from sched_vizual import RadioScheduleVisualizer

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
            print(
                f"Успешно подключено к БД '{self.database}' на сервере '{self.server}'"
            )

        except pyodbc.Error as e:
            print(f"Ошибка подключения к БД: {e}")
            raise

    def disconnect(self) -> None:
        """Закрытие соединения с БД"""
        if self.connection:
            self.connection.close()
            print("🔌 Соединение с БД закрыто")

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
            print(f"Запрос выполнен успешно. DataFrame размер: {self.df.shape}")
            return self.df
        except Exception as e:
            print(f"Ошибка выполнения запроса: {e}")
            raise

    def query_radio_points(self) -> Dict[int, str]:
        """
        Получение списка всех RadioID и их названий
        """
        query = "SELECT DISTINCT PointID, Point FROM dbo.Points ORDER BY PointID"
        try:
            radios_df = pd.read_sql(query, self.connection)
            print(f"Получено {len(radios_df)} уникальных PointID")
            return dict(zip(radios_df['PointID'], radios_df['Point']))
        except Exception as e:
            print(f"Ошибка получения PointID: {e}")
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
        print("📻 Доступные радиостанции:")
        for radio in radios:
            print(f"  - {radio}: {radios[radio]}")

        try:
            radio_point_id = input("\nВведите PointID для получения данных: ")
            radio_point_id = int(radio_point_id)
        except ValueError:
            print("Некорректный PointID. Должно быть целое число.")
            return

        df = db.query_scheds(radio_point_id, date_start=date_start, date_end=date_end)
        if not df.empty:
            print(df.head(10))
            print(f"\nВсего таблиц в БД: {len(df)}")
            df.to_csv("scheds_orders_tmp.csv", index=False)

    except Exception as e:
        print(f"Произошла ошибка: {e}")

    finally:
        # Закрытие соединения
        db.disconnect()

    # Вывод первых строк для проверки
    print("Пример данных:")
    print(df.head(10))
    print("\n")

    # Создание визуализатора и подготовка данных
    radio_name = radios[radio_point_id] if radio_point_id in radios else f"PointID {radio_point_id}"
    visualizer = RadioScheduleVisualizer(df, radio_point_id, radio_name=radio_name)
    visualizer.get_figure().show()


if __name__ == "__main__":
    main()

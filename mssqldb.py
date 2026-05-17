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
                f"✅ Успешно подключено к БД '{self.database}' на сервере '{self.server}'"
            )

        except pyodbc.Error as e:
            print(f"❌ Ошибка подключения к БД: {e}")
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
            H.SchID, 
            H.SchDate, 
            H.Start, 
            H.Stop, 
            H.State, 
            H.ClipID, 
            H.CatID, 
            H.PlanID, 
            H.Bonus, 
            H.MarkID, 
            H.Rate, 
            H.Cat, 
            H.OrderID, 
            H.Clip, 
            H.RealDur, 
            H.Attach, 
            O.RadioID, 
            O.Title, 
            O.Customer, 
            O.Client, 
            O.Responsible
        FROM            
            dbo.Scheds_V AS H 
        INNER JOIN 
            dbo.Orders_V AS O ON H.OrderID = O.OrderID
        WHERE 
            O.RadioID = ?
            AND H.SchDate BETWEEN CONVERT(date, ?) AND CONVERT(date, ?)
        ORDER BY 
            H.SchDate, 
            H.Start
        """
        try:
            self.df = pd.read_sql(query, self.connection, params=[radio_id, date_start, date_end])
            print(f"✅ Запрос выполнен успешно. DataFrame размер: {self.df.shape}")
            return self.df
        except Exception as e:
            print(f"❌ Ошибка выполнения запроса: {e}")
            raise

    def query_radios(self) -> List[Dict[str, Union[int, str]]]:
        """
        Получение списка всех RadioID и их названий
        """
        query = "SELECT DISTINCT RadioID, Radio FROM dbo.Radios ORDER BY RadioID"
        try:
            radios_df = pd.read_sql(query, self.connection)
            print(f"✅ Получено {len(radios_df)} уникальных RadioID")
            return radios_df.to_dict('records')
        except Exception as e:
            print(f"❌ Ошибка получения RadioID: {e}")
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
    date_start = "2024-04-16"
    date_end = "2024-04-22"
    try:
        # Подключение к БД
        db.connect()

        # Использование DataFrame для анализа данных
        radios = db.query_radios()
        print("📻 Доступные радиостанции:")
        for radio in radios:
            print(f"  - {radio['RadioID']}: {radio['Radio']}")

        try:
            radio_id = input("\nВведите RadioID для получения данных: ")
            radio_id = int(radio_id)
        except ValueError:
            print("❌ Некорректный RadioID. Должно быть целое число.")
            return

        df = db.query_scheds(radio_id, date_start=date_start, date_end=date_end)
        if not df.empty:
            print(df.head(10))
            print(f"\nВсего таблиц в БД: {len(df)}")
            # df.to_csv("scheds_orders_tmp.csv", index=False)

    except Exception as e:
        print(f"Произошла ошибка: {e}")

    finally:
        # Закрытие соединения
        db.disconnect()
        # Создание визуализатора и подготовка данных
    visualizer = RadioScheduleVisualizer(df)

    # Вывод первых строк для проверки
    print("Пример данных:")
    print(
        df[["SchDate", "Start", "Stop", "Customer", "Start_Time", "RadioID"]].head(10)
    )
    print("\n")

    # Запуск визуализации
    radio_name = radios[radio_id-1]["Radio"] 
    visualizer.interactive_visualization(radio_id, radio_name)


if __name__ == "__main__":
    main()

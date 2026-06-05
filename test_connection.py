import os
import pyodbc
import dotenv

dotenv.load_dotenv()  # Загружаем переменные окружения из .env файла

print([d for d in pyodbc.drivers() if "SQL Server" in d])

# 1. Задаем параметры подключения 
SERVER_NAME = os.getenv('SERVER_NAME')              # Локальный экземпляр SQL Express
DATABASE_NAME = os.getenv('DB_NAME')              # Имя вашей базы данных
USER_ID = os.getenv('DB_USER')                  # Созданный пользователь
USER_PASSWORD = os.getenv('DB_PASSWORD')           # Пароль пользователя
DRIVER_NAME = os.getenv("DRIVER_NAME") 

# 2. Формируем строку подключения (Connection String)
# ВАЖНО: Убираем параметр Trusted_Connection, так как мы используем логин/пароль
connection_string = (
    f"DRIVER={DRIVER_NAME};"
    f"SERVER={SERVER_NAME};"
    f"DATABASE={DATABASE_NAME};"
    f"UID={USER_ID};"
    f"PWD={USER_PASSWORD};"
    f"ApplicationIntent=ReadOnly;"        # Опционально: указывает серверу на намерение только чтения
)

try:
    # 3. Устанавливаем соединение
    print("Попытка подключения к базе данных...")
    with pyodbc.connect(connection_string) as conn:
        print("Соединение успешно установлено!")
        
        # 4. Создаем курсор для выполнения запросов
        with conn.cursor() as cursor:
            # Пример простого тестового запроса
            cursor.execute("SELECT @@VERSION;")
            row = cursor.fetchone()
            
            print("\nВерсия SQL Server:")
            print(row[0])
            
except pyodbc.Error as e:
    print("\n[Ошибка подключения]")
    print(f"Код ошибки: {e}")

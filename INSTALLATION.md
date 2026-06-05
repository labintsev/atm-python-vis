# Настройка подключения к базе данных

Настройка пользователя с правами «только для чтения» через графический интерфейс SQL Server Management Studio (SSMS) выполняется в три основных этапа.

## Шаг 1. Создание логина на сервере
Логин отвечает за аутентификацию (проверку пароля) при подключении к серверу.

   1. В окне Object Explorer разверните папку вашего сервера.
   2. Разверните папку Security (Безопасность), нажмите правой кнопкой мыши на Logins (Имена входа) и выберите New Login... (Создать имя входа...).
   3. В поле Login name введите имя (например, ReadOnlyUser).
   4. Переключите маркер на SQL Server authentication (Аутентификация SQL Server) и задайте надежный пароль.
   5. Снимите галочку с User must change password at next login (Требовать смену пароля при следующем входе), чтобы избежать проблем при первом удаленном подключении скриптов или программ.
   6. Внизу окна в поле Default database (База данных по умолчанию) выберите вашу целевую базу данных.

## Шаг 2. Привязка к базе данных и ограничение прав
На этом этапе мы создаем пользователя внутри конкретной БД и даем ему роль «только для чтения».

   1. В этом же окне создания логина перейдите на вкладку User Mapping (Сопоставление пользователей) в левой панели.
   2. В верхней таблице найдите вашу базу данных и поставьте напротив нее галочку в столбце Map.
   3. Выделите эту строку кликом мыши.
   4. В нижней таблице (Database role membership) обязательно поставьте галочку напротив роли db_datareader. Это и есть право «только для чтения» (разрешает выполнение SELECT).
   5. Убедитесь, что галочка с роли db_owner или других ролей записи снята.

## Шаг 3. Сохранение настроек

   1. Нажмите кнопку OK внизу окна. Новый пользователь создан.

Если сервер настроен в режиме «Только Windows», войти под локальным SQL-пользователем (таким как ReadOnlyUser) не удастся.Подключитесь к SQL Server под своей учетной записью администратора (через Проверку подлинности Windows / Windows Authentication).  
В обозревателе объектов (Object Explorer) нажмите правой кнопкой мыши на имя самого сервера (корневой элемент дерева) и выберите Свойства (Properties).  
Перейдите в раздел Безопасность (Security).В блоке «Проверка подлинности сервера» выберите пункт Проверка подлинности SQL Server и Windows (Смешанный режим / Mixed Mode).  

Строка для подключения
```
Server=localhost\SQLEXPRESS;Database=master;Trusted_Connection=True;
```

------------------------------
## Как проверить подключение?

   1. В SSMS нажмите кнопку Connect -> Database Engine....
   2. В поле Authentication выберите SQL Server Authentication.
   3. Введите созданный логин и пароль.
   4. Нажмите Options >> (Параметры), перейдите на вкладку Connection Properties (Свойства подключения) и в поле Connect to database выберите вашу БД. Это гарантирует, что TCP-запрос пойдет сразу в нужную базу, так как к системным базам у этого пользователя доступа не будет.

# Установка приложения

## Step 1
В системе должны быть установлены Python и git. 
Клонировать приложение из gihub и установить зависимости:
```
git clone https://github.com/labintsev/atm-python-vis.git
cd atm-python-vis
pip install -r requeirements.txt
```

## Step 2
Создать .env файл

```sh
DB_USER=ReadOnlyUser
DB_PASSWORD=Yourpass234!
DB_NAME=ATM_267
SERVER_NAME = 'localhost\SQLEXPRESS'   
DRIVER_NAME = '{ODBC Driver 17 for SQL Server}'
# Authentication Credentials
AUTH_USERNAME=user
AUTH_PASSWORD=SomePass

# Flask Configuration
SECRET_KEY=your-secret-key-change-this-in-production
```


# Установка веб сервиса

Нам нужен автоматический HTTPS от Let's Encrypt, используем Traefik 
Сервер должен иметь открытые 80 и 443 порты через статический адрес.

------------------------------
## Шаг 1: Скачивание Traefik

   1. Перейдите на официальный GitHub Traefik и скачайте архив для Windows (например, traefik_v3.X.X_windows_amd64.zip).
   2. Распакуйте его в удобную папку, например C:\traefik\. Внутри будет один файл traefik.exe. [3] 

## Шаг 2: Создание конфигурации (Статическая)
В папке C:\traefik\ создайте главный файл конфигурации traefik.yml. Он отвечает за запуск самого сервера, порты и Let's Encrypt.
```
entryPoints:
  web:
    address: ":80"
  websecure:
    address: ":443"

# Включаем чтение настроек из файла
  file:
    filename: "C:/traefik/dynamic_conf.yml"
    watch: true # Traefik будет обновлять настройки на лету при изменении файла
# Настройка автоматического выпуска SSL-сертификатовcertificatesResolvers:
  myresolver:
    acme:
      email: "your-email@example.com" # Укажите вашу почту
      storage: "C:/traefik/acme.json"
      tlsChallenge: {}
```

Создайте в этой же папке пустой файл acme.json — туда Traefik сохранит полученные SSL-сертификаты.

## Шаг 3: Настройка маршрутизации к Flask (Динамическая)
Создайте второй файл dynamic_conf.yml в папке C:\traefik\. Именно здесь мы связываем ваш домен с запущенным Flask-приложением. [4] 
```
http:
  routers:
    # 1. Основной роутер для HTTPS
    flask-secure:
      entryPoints:
        - "websecure"
      rule: "Host(`ваш_домен.com`)" # Укажите ваш домен
      service: "flask-service"
      tls:
        certResolver: "myresolver"

    # 2. Роутер для автоматического редиректа с HTTP на HTTPS
    flask-redirect:
      entryPoints:
        - "web"
      rule: "Host(`ваш_домен.com`)"
      middlewares:
        - "redirect-to-https"
      service: "noop-service" # Техническая заглушка для редиректа

  middlewares:
    redirect-to-https:
      redirectScheme:
        scheme: "https"
        permanent: true

  services:
    # Указываем Traefik, где физически на Windows запущен Flask (Waitress)
    flask-service:
      loadBalancer:
        servers:
          - url: "http://127.0.0.1:8000" # Порт вашего приложения

    # Заглушка для редиректа
    noop-service:
      loadBalancer:
        servers:
          - url: "http://127.0.0.1:8000"
```

## Шаг 4: Запуск Flask (Waitress)

Flask-приложение запускается точно так же, как в классическом варианте (через waitress на порту 8000 локально).

```py
# wsgi.py
from my_app import appfrom waitress import servefrom werkzeug.middleware.proxy_fix import ProxyFix
# Обязательно добавляем ProxyFix, чтобы Flask понимал HTTPS заголовки от Traefik
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
if __name__ == "__main__":
    serve(app, host='127.0.0.1', port=8000, threads=4)
```

Запустите скрипт в вашей консоли: 
```sh
python wsgi.py
```

## Шаг 5: Тестовый запуск Traefik
Откройте командную строку от имени Администратора (это важно, чтобы занять 80 и 443 порты) в папке C:\traefik\ и выполните:
```sh
traefik.exe --configfile=traefik.yml
```

Если домен настроен правильно и смотрит на ваш сервер, Traefik автоматически свяжется с Let's Encrypt, выпустит сертификат в файл acme.json и проксирует трафик на 127.0.0.1:8000.

## Шаг 6: Установка Traefik и Flask как служб Windows
Чтобы всё работало в фоне без открытых окон консоли, оформите обе программы как службы Windows с помощью утилиты NSSM: [5] 

   1. Для Flask:
```sh   
   nssm install FlaskWaitress "C:\путь_к_выделенному_env\Scripts\python.exe" "C:\путь_к_проекту\wsgi.py"
   nssm start FlaskWaitress
```   
   2. Для Traefik:
```
   nssm install TraefikServer "C:\traefik\traefik.exe" "--configfile=C:\traefik\traefik.yml"
   nssm start TraefikServer
```   

Ссылки:    
[1] [https://www.reddit.com](https://www.reddit.com/r/Traefik/comments/pp97jh/guide_that_doesnt_involve_docker/)
[2] [https://doc.traefik.io](https://doc.traefik.io/traefik/v2.0/getting-started/install-traefik/)
[3] [https://medium.com](https://medium.com/@ramanamuttana/install-traefik-on-windows-without-docker-63ede51b5b3e)
[4] [https://doc.traefik.io](https://doc.traefik.io/traefik/providers/file/)
[5] [https://www.reddit.com](https://www.reddit.com/r/flask/comments/126ukqr/how_do_i_deploy_an_app_to_run_locally/)

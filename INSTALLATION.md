# Установка сервиса

Нам нужен автоматический HTTPS от Let's Encrypt, Traefik должен иметь возможность слушать 80 и 443 порты.

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
В системе должны быть установлены Python и git. 
Клонировать приложение из gihub и установить зависимости:
```
git clone https://github.com/labintsev/atm-python-vis.git
cd atm-python-vis
pip install -r requeirements.txt
```

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

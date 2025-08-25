# Kuzya Tray App

Kuzya Tray App — минималистичное Windows‑приложение в системном трее, которое поднимает локальный HTTP‑сервер и позволяет управлять ПК (toggle media, выключение, громкость, mute) из Домовёнка Кузи или любых других источников, умеющих слать HTTP‑запросы.

- Порт по умолчанию: **45583**
- Работает без админ‑прав
- Windows 10/11, Python 3.8+ (проверено на Python 3.12)
- Транспорт: **HTTP GET/POST**
- Аудио: через **pycaw** (Core Audio) для стабильных COM‑сигнатур

## Возможности (эндпоинты)

Все ответы — JSON. Примеры — без токена (по запросу пользователя):

- `GET /state` → `{"ok":true,"value":1}`  
- `GET /toggle` → Toggle Play/Pause (аппаратно: VK→SCAN(E0 22)→keybd_event)  
- `GET /shutdown` (синонимы `/off`, `/power_off`) → выключение ПК  
- `GET /get_volume` → `{"ok":true,"value":0..100}`  
- `GET /set_volume?value=N` → `{"ok":true,"value":N}` (принимает также `{N}`)  
- `GET /volume_up?step=5`, `GET /volume_down?step=5` → шаг по громкости  
- `GET /get_mute` → `{"ok":true,"value":0|1}`  
- `GET /mute`, `GET /unmute`, `GET /toggle_mute`

## Установка

1. Установите Python 3.12 (x64). Убедитесь, что Python в PATH или используйте полный путь к `python.exe`.
2. Поставьте зависимости:
   ```bat
   pip install pycaw comtypes PySide6
   ```
3. Сохраните файл `kuzya_tray_app.py` (ваша текущая версия приложения).

## Запуск

```bat
"C:\Users\wyrte.WYRTENSI.000\AppData\Local\Programs\Python\Python312\python.exe" kuzya_tray_app.py --port 45583
```
При старте иконка появится в системном трее. Сообщение в трее покажет URL вида `http://<LAN-IP>:45583`.

### Примеры запросов

```bat
curl http://127.0.0.1:45583/state
curl http://127.0.0.1:45583/toggle
curl "http://127.0.0.1:45583/set_volume?value=51"
curl http://127.0.0.1:45583/get_mute
curl http://127.0.0.1:45583/toggle_mute
```

### Проброс порта и брандмауэр

- Разрешите входящие соединения TCP **45583** в Windows Defender Firewall.
- Если нужен доступ извне (WAN): настройте переадресацию порта **45583 → 192.168.0.103:45583** на роутере.

## Интеграция с Домовёнком Кузей

В Кузе создавайте действия типа **HTTP GET** по нужным URL. Готовые адреса для LAN/WAN — в `agents.md`.
- LAN: `http://192.168.0.103:45583/...`
- WAN: `http://46.48.26.83:45583/...`

## Безопасность

Если открываете порт в интернет, используйте один или несколько вариантов защиты:
- ограничение по IP (на роутере), 
- прокси с авторизацией, 
- VPN, 
- добавьте `?token=секрет` и включите проверку токена в приложении (опция в коде предусмотрена).

## Автозапуск (опционально)

- **Планировщик задач Windows**: создать задачу «При входе в систему» с запуском `python.exe kuzya_tray_app.py --port 45583`.
- Или положить ярлык в `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup`.

## Диагностика / FAQ

- `call takes exactly N arguments (M given)` или `The parameter is incorrect.`  
  → это про неверные COM‑сигнатуры. Приложение использует **pycaw**, где интерфейсы корректны. Убедитесь, что `pip show pycaw` есть и `/state` выводит путь к pycaw.

- Проверка окружения:
  ```bat
  python -c "import sys,pycaw,comtypes; print(sys.executable); print(pycaw.__file__); import comtypes as c; print(c.__file__)"
  ```

- `/state` показывает путь к pycaw/comtypes — удобно для быстрой проверки, чем именно пользуется приложение.

## Лицензия

Этот репозиторий/скрипт можно использовать свободно в личных целях.
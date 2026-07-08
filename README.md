# 📡 Telegram ID Parser

Парсер для извлечения Telegram ID из конфигурационных ссылок (vless://, vmess://, hysteria:// и другие).  
Работает в автоматическом режиме через GitHub Actions, умеет находить ID даже в закодированных полях, отслеживать изменения и показывает результаты в веб-интерфейсе.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-Auto--update-brightgreen)](https://github.com/features/actions)

---

## 🎯 Назначение

Инструмент сканирует конфигурационные ссылки (vless://, vmess://, trojan://, hysteria://, tuic:// и другие) и извлекает упоминания Telegram-каналов в формате `@username`.

**Что умеет:**
- Поддерживает **7 протоколов** (vless, vmess, trojan, ss, ssr, hysteria, tuic).
- Декодирует **base64**-закодированные параметры (актуально для vmess:// и подобных).
- Ищет ID **во всех полях** ссылки, включая `path`, `extra`, `remarks`.
- Очищает ID от лишнего текста (например, `@channel (канал)` → `@channel`).
- Работает **инкрементально** — показывает, какие ID появились или исчезли.
- Сохраняет **промежуточные результаты**, чтобы не потерять данные при сбое.
- Отдаёт результаты в **веб-интерфейсе** (GitHub Pages).

---

## 🚀 Быстрый старт

### Установка

```bash
git clone https://github.com/your-username/tg_id_scraper.git
cd tg_id_scraper
pip install -r requirements.txt
```

### Запуск

1. Создайте файл `input.txt` со ссылками на конфигурационные файлы (по одной на строку):
   ```
   https://raw.githubusercontent.com/user/configs/main/vless.txt
   https://example.com/subscription.txt
   ```

2. Запустите парсер:
   ```bash
   python main.py --input-file input.txt --output output
   ```

   **Дополнительные параметры:**
   - `--workers 15` — количество параллельных загрузчиков (по умолчанию 10).
   - `--no-incremental` — отключить инкрементальный режим (всегда перезаписывать).
   - `-v` — подробный вывод.

3. Результат появится в папке `output/`:
   - `telegram_ids.py` — список URL-адресов каналов в формате Python-модуля (можно импортировать).
   - `telegram_ids.txt` — простой список ID с `@`.
   - `parsed_configs.json` — полные данные парсинга.
   - `changes.txt` — отчёт о добавленных и удалённых ID (при инкрементальном режиме).

---

## 📁 Выходные данные

### `telegram_ids.py` (Python-модуль)
```python
SOURCE_URLS = [
    "https://t.me/s/Leecher56",
    "https://t.me/s/bored_vpn",
    "https://t.me/s/NetFlowTools",
    "https://t.me/s/MARAMBASHI",
    "https://t.me/s/meliproxyy",
    "https://t.me/s/FarazV2ray",
]
```

### `telegram_ids.txt`
```
@Leecher56
@bored_vpn
@NetFlowTools
@MARAMBASHI
@meliproxyy
@FarazV2ray
```

### `changes.txt` (пример)
```
Added IDs:
  + @new_channel
  + @another_one
Removed IDs:
  - @old_channel
```

---

## 🌐 Веб-интерфейс

После каждого запуска на GitHub Pages публикуется страница с результатами.  
Перейдите по ссылке, чтобы увидеть все найденные каналы в виде удобного списка со ссылками:

👉 [**Открыть веб-интерфейс**](https://LexterS999.github.io/tg_id_scraper/)  
*(замените `ваш-username` на имя вашего GitHub-аккаунта)*

Страница обновляется автоматически после каждого запуска парсера.  
Вы можете использовать её для быстрого просмотра результатов без необходимости скачивать файлы.

---

## ⚙️ GitHub Actions (Автоматизация)

Проект настроен для автоматического запуска каждые 3 часа.  
Результаты коммитятся в репозиторий, а веб-интерфейс публикуется на GitHub Pages.

### Workflow: `.github/workflows/parse.yml`

```yaml
name: Parse Telegram Channels

on:
  schedule:
    - cron: '0 */3 * * *'
  workflow_dispatch:

jobs:
  parse:
    runs-on: ubuntu-latest
    permissions:
      contents: write
      pages: write
      id-token: write

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Run parser
        run: |
          python main.py --input-file input.txt --output output --workers 15

      - name: Copy web interface
        run: |
          mkdir -p docs
          cp docs/index.html docs/
          cp output/telegram_ids.txt docs/telegram_ids.txt || true

      - name: Commit and push
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Action"
          git add -f output/telegram_ids.py output/telegram_ids.txt output/changes.txt docs/telegram_ids.txt || true
          git diff --staged --quiet || git commit -m "Update Telegram IDs (auto)"
          git push

      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: telegram-ids
          path: output/

      - name: Deploy to GitHub Pages
        uses: actions/deploy-pages@v4
```

### Ручной запуск
Перейдите во вкладку **Actions** → **Parse Telegram Channels** → **Run workflow**.

---

## 📂 Структура проекта

```
tg_id_scraper/
├── .github/workflows/parse.yml   # GitHub Actions
├── parser/
│   ├── __init__.py
│   ├── core.py                   # Основной парсер (новые протоколы, base64, умный поиск)
│   ├── extractors.py             # Извлечение ID
│   ├── utils.py                  # Загрузка, кэш, промежуточное сохранение
│   └── validators.py             # Валидация ссылок и очистка ID
├── examples/
│   ├── run_example.py
│   └── sample.txt
├── tests/
│   ├── test_core.py
│   ├── test_extractors.py
│   ├── test_utils.py             # Тесты для утилит
│   └── test_integration.py       # Интеграционные тесты
├── docs/
│   └── index.html                # Веб-интерфейс для GitHub Pages
├── output/                       # Результаты (создаётся автоматически)
│   ├── .gitkeep
│   ├── telegram_ids.py
│   ├── telegram_ids.txt
│   ├── parsed_configs.json
│   └── changes.txt
├── .gitignore
├── config.py                     # Настройки
├── input.txt                     # Ссылки на конфигурационные файлы
├── main.py                       # Точка входа
├── README.md                     # Этот файл
└── requirements.txt              # Зависимости
```

---

## 🔧 Конфигурация

Все настройки в `config.py`:

```python
# Поддерживаемые протоколы (расширенный список)
SUPPORTED_PROTOCOLS = [
    'vless://', 'vmess://', 'trojan://', 'ss://', 'ssr://',
    'hysteria://', 'tuic://'
]

# Параметры для проверки (сейчас проверяются все, но можно сузить)
URL_PARAMS_TO_CHECK = ['host', 'sni', 'server', 'domain', 'add']

# Время жизни кэша (секунды)
CACHE_TTL = 3600

# Количество параллельных воркеров по умолчанию
DEFAULT_WORKERS = 10
```

---

## 📦 Зависимости

- `requests >= 2.28.0` — загрузка конфигураций
- `urllib3 >= 1.26.0` — HTTP-клиент
- `pytest >= 7.0.0` — тесты

---

## 🧪 Тестирование

```bash
pytest tests/
```

---

## 🔒 .gitignore

Файлы результатов (`output/*.py`, `output/*.txt`, `docs/telegram_ids.txt`) **не игнорируются**, чтобы они попадали в репозиторий.  
Остальные временные и системные файлы — игнорируются.

---

## 📝 Лицензия

MIT. Подробнее в файле `LICENSE`.

---

## 🤝 Вклад

1. Форкните репозиторий.
2. Создайте ветку для изменений.
3. Внесите изменения и добавьте тесты.
4. Отправьте Pull Request.

---

## ❓ Часто задаваемые вопросы

**Что делать, если файлы не обновляются в репозитории?**  
Проверьте, что в `.gitignore` нет строк, игнорирующих `output/*.py` или `docs/telegram_ids.txt`. Если есть — удалите их и сделайте коммит.

**Как изменить расписание запуска?**  
Измените `cron` в `.github/workflows/parse.yml`:
```yaml
schedule:
  - cron: '0 */6 * * *'   # Каждые 6 часов
```

**Можно ли использовать одну ссылку вместо списка?**  
Да, через флаг `--url`:
```bash
python main.py --url https://example.com/config.txt --output output
```

**Где посмотреть веб-интерфейс?**  
После первого успешного запуска Actions страница будет доступна по адресу:  
👉 [**https://LexterS999.github.io/tg_id_scraper/**](https://LexterS999.github.io/tg_id_scraper/)  
*(замените `ваш-username` на имя вашего GitHub-аккаунта)*

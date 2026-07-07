# 📡 Telegram ID Parser

Парсер для извлечения Telegram ID из конфигурационных ссылок (vless://, vmess://, и т.д.) с автоматическим обновлением через GitHub Actions.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-Auto--update-brightgreen)](https://github.com/features/actions)

---

## 🎯 Назначение

Инструмент сканирует конфигурационные ссылки (vless://, vmess://, и т.д.) и извлекает упоминания Telegram-каналов в формате `@username`. Результат сохраняется в виде списка URL-адресов каналов в формате Python-списка, готового для использования в других скриптах.

### Пример использования

**Входные данные** (конфигурационная ссылка):
```
vless://03707fb7...@104.16.75.234:443?path=/&security=tls#@iguanaVPN6
```

**Извлечённый ID:** `@iguanaVPN6`  
**Итоговый URL:** `https://t.me/s/iguanaVPN6`

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

3. Результат появится в папке `output/`:
   - `telegram_ids.json` — список URL-адресов каналов в формате Python
   - `telegram_ids.txt` — простой список ID с `@`
   - `parsed_configs.json` — полные данные парсинга

---

## 📁 Выходные данные

### `telegram_ids.json`
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

---

## ⚙️ GitHub Actions (Автоматизация)

Проект настроен для автоматического запуска каждые 3 часа через GitHub Actions.

### Workflow: `.github/workflows/parse.yml`

```yaml
name: Parse Telegram Channels

on:
  schedule:
    - cron: '0 */3 * * *'   # Каждые 3 часа
  workflow_dispatch:         # Ручной запуск

jobs:
  parse:
    runs-on: ubuntu-latest
    permissions:
      contents: write

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
          python main.py --input-file input.txt --output output

      - name: Commit and push if changes
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Action"
          mkdir -p output
          git add -f output/telegram_ids.txt output/telegram_ids.json || true
          git diff --staged --quiet || git commit -m "Update Telegram IDs (auto)"
          git push
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: telegram-ids
          path: output/
```

### Ручной запуск
Перейдите во вкладку **Actions** → **Parse Telegram Channels** → **Run workflow**.

---

## 📂 Структура проекта

```
tg_id_scraper/
├── .github/
│   └── workflows/
│       └── parse.yml           # GitHub Actions workflow
├── parser/
│   ├── __init__.py
│   ├── core.py                 # Основной парсер
│   ├── extractors.py           # Извлечение Telegram ID
│   └── utils.py                # Вспомогательные функции
├── examples/
│   ├── run_example.py          # Пример использования
│   └── sample.txt              # Пример входных данных
├── tests/
│   ├── test_core.py            # Тесты парсера
│   └── test_extractors.py      # Тесты извлечения
├── output/                     # Результаты (создаётся автоматически)
│   ├── .gitkeep
│   ├── telegram_ids.json
│   ├── telegram_ids.txt
│   └── parsed_configs.json
├── .gitignore
├── config.py                   # Настройки (регулярки, форматы)
├── input.txt                   # Ссылки на конфигурационные файлы
├── main.py                     # Точка входа
├── README.md                   # Этот файл
└── requirements.txt            # Зависимости
```

---

## 🔧 Конфигурация

Все настройки хранятся в `config.py`:

```python
# Регулярные выражения для поиска Telegram ID
TELEGRAM_ID_PATTERN = r'@[a-zA-Z0-9_]{5,32}'

# Параметры URL, которые проверяются на наличие ID
URL_PARAMS_TO_CHECK = ['host', 'sni', 'server', 'domain', 'add']

# Поддерживаемые протоколы
SUPPORTED_PROTOCOLS = ['vless://', 'trojan://', 'vmess://', 'ss://', 'ssr://']

# Формат выходных файлов
DEFAULT_OUTPUT_FORMAT = "both"  # 'json', 'txt', 'both'
```

---

## 📦 Зависимости

- `requests >= 2.28.0` — для загрузки конфигураций
- `urllib3 >= 1.26.0` — HTTP-клиент
- `pytest >= 7.0.0` — для тестов

---

## 🧪 Тестирование

```bash
pytest tests/
```

---

## 🔒 .gitignore

Файлы `output/*.json` и `output/*.txt` **не игнорируются**, чтобы результаты сохранялись в репозитории. Остальные стандартные для Python файлы игнорируются.

```gitignore
# Output files — сохраняются для CI/CD
!output/.gitkeep
```

---

## 📝 Лицензия

Проект распространяется под лицензией **MIT**. Подробнее в файле `LICENSE`.

---

## 🤝 Вклад

1. Форкните репозиторий
2. Создайте ветку для изменений
3. Внесите изменения и добавьте тесты
4. Отправьте Pull Request

---

## ❓ Часто задаваемые вопросы

### Что делать, если файлы не обновляются в репозитории?
Проверьте, что в `.gitignore` нет строк, игнорирующих `output/*.json` или `output/*.txt`. Если они есть — удалите их и сделайте коммит.

### Как изменить расписание запуска?
Измените `cron` в `.github/workflows/parse.yml`:
```yaml
schedule:
  - cron: '0 */6 * * *'   # Каждые 6 часов
```

### Можно ли использовать одну ссылку вместо списка?
Да, используйте флаг `--url`:
```bash
python main.py --url https://example.com/config.txt --output output
```

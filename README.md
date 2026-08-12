# Scanner service

Асинхронное приложение на Python (FastStream) для сбора данных о стаканах ордеров с криптовалютных бирж и поиска арбитражных групп.

- CCXT Publisher для загрузки маркетов, группировки символов и публикации в RabbitMQ.
- CCXT Consumer & Publisher получение групп символов из очереди и загрузка стаканов order books очередь RAbbitMQ.



## Навигация
- [Стек технологий](#стек-технологий)
- [Возможности](#возможности)
- [Структура проекта](#структура-проекта)
- [Быстрый старт](#быстрый-старт)
- [Pipeline данных](#pipeline-данных)
- [Формат сообщений](#формат-сообщений)



## Стек технологий

- **FastStream** — брокер сообщений (RabbitMQ)
- **CCXT** — унифицированный API к 100+ биржам
- **Pydantic Settings** — конфигурация через `.env`
- **Pydantic DTO** — валидация и типизация сообщений


## Возможности

- **Многобиржевой сбор данных** — одновременная работа с несколькими биржами (bybit, mexc, binance и др.)
- **Группировка символов** — объединение торговых пар по `(base, quote/settle)` группам
- **Распределённая архитектура** — каждая биржа работает через пул менеджеров, обеспечивающий fair scheduling
- **Прокси-поддержка** — конфигурация прокси для обхода ограничений бирж
- **RabbitMQ интеграция** — обмен данными между компонентами через очереди сообщений
- **Pipeline данных** — market loading → grouping → orderbook fetching → aggregation
- **DTO-контракты** — строгая типизация сообщений через Pydantic models
- **Два режима запуска** — Publisher+Consumer или Consumer only


## Структура проекта

```
src/
├── main.py          # FastStream application + lifecycle hooks
├── config.py        # Config via pydantic-settings
├── broker.py        # RabbitMQ publisher/subscriber logic
├── factories.py     # CCXT exchange factory
├── utils.py         # Pool[T] for fair scheduling, get_groups
├── adapters/        # Exchange adapters
│   └── ccxt_adapter.py  # CCXT adapter + DTO mapping
├── core/            # Core models & exceptions
│   ├── models.py    # Pydantic DTO (Exchange, Symbol, Orderbook)
│   └── exceptions.py # Custom exceptions
├── services/        # Business logic
│   └── managers.py  # ExchangeManager
├── tests/           # Unit tests
│   ├── conftest.py
│   ├── mock_data.py
│   ├── test_adapters.py
│   ├── test_factories.py
│   ├── test_managers.py
│   └── test_utils.py
├── sandbox.py       # Interactive sandbox
├── Dockerfile
├── pytest.ini
└── requirements.txt
```


## Настройки
Переменные окружения:
```bash
# Exchanges & Proxies
EXCHANGES=bybit,mexc,binance
PROXIES=http://proxy1:8080,http://proxy2:8080,

# RabbitMQ
RMQ_HOST=localhost
RMQ_PORT=5672
RMQ_USER=guest
RMQ_PASS=guest

# Pipeline
MIN_LENGTH=100      # мин. сообщений в очереди перед публикацией
TIMEOUT=30          # интервал publish-задания (сек)
```


## Быстрый старт

### 1. Установка

Копировать репозиторий
```bash
git clone https://github.com/iadzhak-arb/scanner.git
cd scanner
```

Настроить окружение
```bash
# Создайте виртуальное окружение
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Установите зависимости
pip install -r requirements.txt
```

Запустить RabbitMQ
```bash
docker run -d --name rabbitmq -p 5672:5672 -p 15672:15672 \
  rabbitmq:3-management
```

### 2. Запуск

> Перед запуском необходимо настроить переменные окружения.

Publisher + Consumer
```bash
faststream run src.main:app --publish
```

Consumer only
```bash
faststream run src.main:app
```


## Pipeline данных

1. **Market Loading** — `CCXTAdapter.load_markets()` загружает все символы биржи
2. **Grouping** — `get_groups()` группирует символы по `(base, settle/quote)`
3. **Publishing** — группы публикуются в `queue_groups` (если `MIN_LENGTH` достигнут)
4. **Orderbook Fetching** — `handle_groups` получает группы, запрашивает стаканы со всех бирж
5. **Orderbook Publishing** — собранные `OrderbookDTO` публикуются в `queue_orderbooks`


## Формат сообщений

### `queue_groups`

**Тип сообщения:** `list[SymbolGroupDTO]` — список групп, образующих arbitrage-возможность.

Каждая группа объединяет один и тот же `(base, quote/settle)` по разным биржам и/или типам рынка.

```json
[
  {
    "symbol": {
      "id": "BTC/USDT:USDT",
      "market": "swap",
      "base": "BTC",
      "quote": "USDT",
      "settle": "USDT"
    },
    "exchanges": [
      { "id": "bybit", "name": "Bybit" },
      { "id": "binance", "name": "Binance" }
    ]
  }
]
```

| Поле | Тип | Описание |
|------|-----|----------|
| `symbol.id` | `str` | Торговый символ в формате CCXT (например `BTC/USDT:USDT`) |
| `symbol.market` | `str` | Тип рынка: `spot`, `swap`, `future` |
| `symbol.base` | `str` | Базовая валюта |
| `symbol.quote` | `str` | Котировочная валюта |
| `symbol.settle` | `str \| null` | Валюта расчётов (для фьючерсов/свапов) |
| `exchanges` | `list` | Список бирж, где доступен данный символ |

---

### `queue_orderbooks`

**Тип сообщения:** `list[OrderbookDTO]` — агрегированные стаканы ордеров.

```json
[
  {
    "symbol": {
      "id": "BTC/USDT:USDT",
      "market": "swap",
      "base": "BTC",
      "quote": "USDT",
      "settle": "USDT"
    },
    "exchange": {
      "id": "bybit",
      "name": "Bybit"
    },
    "timestamp": 1720000000.0,
    "asks": [[21000.5, 1.25], [21001.0, 0.50]],
    "bids": [[20999.5, 2.00], [20998.0, 0.75]]
  }
]
```

| Поле | Тип | Описание |
|------|-----|----------|
| `symbol` | `SymbolDTO` | Описание торгового символа |
| `exchange` | `ExchangeDTO` | Биржа-источник стакана |
| `timestamp` | `float` | Метка времени стакана (Unix epoch, секунды) |
| `asks` | `list[list[float \| int]]` | Аск-сторона: `[price, amount]` |
| `bids` | `list[list[float \| int]]` | Бид-сторона: `[price, amount]` |


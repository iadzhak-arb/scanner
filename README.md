# Arb Scanner

Асинхронное приложение на Python (FastStream) для сбора данных о стаканах ордеров с криптовалютных бирж и поиска арбитражных групп.

## Основные возможности

- **Многобиржевой сбор данных** — одновременная работа с несколькими биржами (bybit, mexc, binance и др.)
- **Группировка символов** — объединение торговых пар по группам
- **Распределённая архитектура** — каждая биржа работает через пул менеджеров, обеспечивающий fair scheduling
- **Прокси-поддержка** — конфигурация прокси для обхода ограничений бирж
- **RabbitMQ интеграция** — обмен данными между компонентами через очереди сообщений

## Архитектура

```
┌─────────────────┐
│  Publisher      │  publish_task — периодический сбор рынков → группировка → публикация
│  (groups queue) │
└──────┬──────────┘
       │  queue_groups
       ▼
┌─────────────────┐
│  Subscriber     │  handle_groups — fetch orderbooks → публикация
│  (groups queue) │
└──────┬──────────┘
       │  queue_orderbooks
       ▼
  [Downstream consumer]

```

### Компоненты

| Компонент | Описание |
|-----------|----------|
| `src/main.py` | Точка входа, lifecycle-хуки FastStream (`on_startup`, `on_shutdown`) |
| `src/factories.py` | Фабрика CCXT-бирж |
| `src/adapters/ccxt_adapter.py` | Адаптер поверх ccxt.async_support, конвертация в DTO |
| `src/services/managers.py` | `ExchangeManager` — управление набором бирж |
| `src/utils.py` | `Pool[T]` — кольцевой пул для fair scheduling менеджеров |
| `src/broker.py` | Конфигурация RabbitMQ, subscriber/publisher логика |
| `src/config.py` | Настройки через `.env` (pydantic-settings) |

## Технологии

- Python 3.12+
- [ccxt](https://github.com/ccxt/ccxt) — унифицированный API к 100+ биржам
- [FastStream](https://faststream.airt.ai/) — брокер сообщений (RabbitMQ)
- [Pydantic](https://docs.pydantic.dev/) — валидация и конфигурация


## Установка

```bash
# Виртуальное окружение
python -m venv .venv
source .venv/bin/activate      # Linux / Mac
# .venv\Scripts\activate       # Windows

# Зависимости
pip install -r requirements.txt
```

## Настройка

Скопируйте `.test.env` и отредактируйте `.env`:

```env
EXCHANGES=bybit,mexc,binance
PROXIES=http://proxy1:8080,http://proxy2:8080,

RMQ_HOST=localhost
RMQ_PORT=5672
RMQ_USER=guest
RMQ_PASS=guest

MIN_LENGTH=100      # мин. сообщений в очереди перед публикацией
TIMEOUT=30          # интервал publish-задания (сек)
```

## Запуск

```bash
# С публикацией групп 
faststream run src.main:app --publish

# Без публикаций
faststream run src.main:app
```

### Контексты запуска

| Режим | Флаг | Поведение |
|-------|------|-----------|
| Publisher + Consumer | `--publish` | Подписка на `groups` + `orderbooks`, периодический publish |
| Consumer only | *(по умолчанию)* | Только подписка на `groups`, обработка и публикация orderbooks |

## Тесты

```bash
pytest
```

## Структура

```
.
├── src/
│   ├── adapters/
│   │   └── ccxt_adapter.py      # CCXT адаптер + DTO маппинг
│   ├── core/
│   │   ├── exceptions.py        # Пользовательские исключения
│   │   └── models.py            # Pydantic DTO (Exchange, Symbol, Orderbook)
│   ├── services/
│   │   └── managers.py          # ExchangeManager
│   ├── broker.py                # RabbitMQ конфигурация
│   ├── config.py                # Settings (.env)
│   ├── factories.py             # Фабрика бирж
│   ├── main.py                  # FastStream app + lifecycle
│   └── utils.py                 # Pool, get_groups
├── tests/
│   ├── conftest.py
│   ├── mock_data.py             # Моковые данные для тестов
│   ├── test_adapters.py
│   ├── test_factories.py
│   ├── test_managers.py
│   └── test_utils.py
├── Dockerfile
├── pytest.ini
├── requirements.txt
└── sandbox.py
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

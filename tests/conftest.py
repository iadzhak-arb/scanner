from unittest import mock

import pytest

import ccxt.async_support as ccxt

from src.core.models import ExchangeDTO, SymbolDTO, SymbolGroupDTO


@pytest.fixture
def mock_data_and_groups():
    data = {
        'ex1': {
            'A/B': {
                'id': 'A/B',
                'base': 'A',
                'quote': 'B',
                'settle': None,
                'market': 'spot'
            },
            'A/B:B': {
                'id': 'A/B:B',
                'base': 'A',
                'quote': 'B',
                'settle': 'B',
                'market': 'swap'
            },
            'C/B': {
                'id': 'C/B',
                'base': 'C',
                'quote': 'B',
                'settle': None,
                'market': 'spot'
            },
        },
        'ex2': {
            'A/B:B': {
                'id': 'A/B:B',
                'base': 'A',
                'quote': 'B',
                'settle': 'B',
                'market': 'swap'
            },
            'C/A:B': {
                'id': 'C/A:B',
                'base': 'C',
                'quote': 'A',
                'settle': 'B',
                'market': 'swap'
            },
        }
    }
    groups = {
        ('A', 'B'): {'A/B': ['ex1'], 'A/B:B': ['ex1', 'ex2']},
        ('C', 'B'): {'C/B': ['ex1'], 'C/A:B': ['ex2']}
    }
    return data, groups


@pytest.fixture
def mock_market_data(mock_data_and_groups):
    mock_data, mock_groups = mock_data_and_groups
    all_symbols = {}
    all_exchanges = {}

    data_input = []
    for ex, ss in mock_data.items():
        exchange = ExchangeDTO(id=ex, name=ex.upper())
        all_exchanges[ex] = exchange
        symbols = [SymbolDTO(**s) for s in ss.values()]
        for s in symbols:
            if s.id not in all_symbols:
                all_symbols[s.id] = s
        data_input.append((exchange, symbols))

    data_output = []
    for g in mock_groups.values():
        current = []
        for s, exs in g.items():
            current.append(
                SymbolGroupDTO(
                    symbol=all_symbols[s],
                    exchanges=[all_exchanges[ex] for ex in exs]
                )
            )
        data_output.append(current)

    return data_input, data_output


@pytest.fixture
def mock_exchanges(mock_market_data, mock_data_and_groups):
    mock_load_markets, _ = mock_market_data
    load_markets, _ = mock_data_and_groups
    mock_exchanges = []
    for ex, markets in mock_load_markets:
        mock_ex = mock.create_autospec(ccxt.Exchange())
        mock_ex.id = ex.id
        mock_ex.name = ex.name
        mock_ex.load_markets.return_value = load_markets[ex.id]
        mock_exchanges.append(mock_ex)
    return mock_exchanges, mock_load_markets


@pytest.fixture
def mock_manager_with_data(mock_market_data, mock_manager):
    mock_markets, _ = mock_market_data
    mock_manager.load_markets = mock.AsyncMock(return_value=mock_markets)
    return mock_manager, mock_markets

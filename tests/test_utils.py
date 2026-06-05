import asyncio
from unittest import mock

import pytest
from deepdiff import DeepDiff

from src.utils import get_groups, Pool


class TestGetGroups:

    def test_valid(self, mock_market_data):
        data_input, data_output = mock_market_data
        data = get_groups(data_input)
        assert isinstance(data, list), 'Должен вернуться list.'
        assert len(data) == len(
            data_output), 'Количество групп не совпадает с ожидаемым.'
        diff = DeepDiff(data, data_output, ignore_order=True)
        assert diff == {}, f'{diff}'

    def test_empty(self):
        data_input = []
        data_output = []
        data = get_groups(data_input)
        assert isinstance(data, list), 'Должен вернуться list.'
        assert data == data_output, f'Некорректное формирование групп. {data_input=}'


@pytest.mark.asyncio
class TestPool:
    async def test_valid(self):
        mock_data = [1, 2, 3]
        pool = Pool(*mock_data)
        for i in range(len(mock_data) + 2):
            async with pool.get(timeout=1) as item:
                assert item == mock_data[i % len(mock_data)]

    async def test_timeout_error(self):
        pool = Pool()
        with pytest.raises(asyncio.TimeoutError):
            async with pool.get(timeout=1) as item:
                pass

    async def test_add(self):
        mock_data = [1, 2, 3]
        pool = Pool()
        pool.add(*mock_data)
        for i in range(len(mock_data)):
            async with pool.get(timeout=1) as item:
                assert item == mock_data[i]

    async def test_exception(self):
        mock_data = mock.AsyncMock(side_effect=Exception)
        pool = Pool()
        pool.add(mock_data)
        with pytest.raises(Exception):
            try:
                async with pool.get(timeout=1) as item:
                    await item()
            except asyncio.TimeoutError:
                pass

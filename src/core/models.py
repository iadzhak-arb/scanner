from pydantic import BaseModel, ConfigDict


class ExchangeDTO(BaseModel):
    id: str
    name: str
    model_config = ConfigDict(from_attributes=True)


class SymbolDTO(BaseModel):
    id: str
    market: str
    base: str
    quote: str
    settle: str | None = None


class SymbolGroupDTO(BaseModel):
    symbol: SymbolDTO
    exchanges: list[ExchangeDTO]
    model_config = ConfigDict(from_attributes=True)


class OrderbookDTO(BaseModel):
    symbol: SymbolDTO
    exchange: ExchangeDTO
    timestamp: float | int
    asks: list[list[float | int]]
    bids: list[list[float | int]]

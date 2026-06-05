from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # CCXT
    EXCHANGES: list[str] = ['bybit', 'mexc']
    PROXIES: list[str] = ['']
    CCXT_MARKETS: set[str] = {'spot', 'swap', 'future'}

    # CONSUMER
    QUEUE_ORDERBOOKS: str = 'orderbooks'

    # PUBLISHER
    QUEUE_GROUPS: str = 'groups'
    MIN_LENGTH: int = 100
    TIMEOUT: int = 30

    # RMQ
    RMQ_HOST: str = 'localhost'
    RMQ_PORT: int = 5672
    RMQ_USER: str = 'guest'
    RMQ_PASS: str = 'guest'

    @property
    def rmq_url(self) -> str:
        return f'amqp://{self.RMQ_USER}:{self.RMQ_PASS}@{self.RMQ_HOST}:{self.RMQ_PORT}'

    model_config = SettingsConfigDict(env_file='.env')


settings = Settings()

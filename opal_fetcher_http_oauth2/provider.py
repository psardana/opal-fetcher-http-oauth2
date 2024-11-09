import os
from typing import Optional
import requests
from opal_common.fetcher.fetch_provider import BaseFetchProvider
from opal_common.fetcher.events import FetcherConfig, FetchEvent
from opal_common.logger import logger
from prometheus_client import Counter, Histogram, Gauge

METRIC_NAMESPACE = 'opal_oauth2_http_fetcher'

OPERATION_FETCH_OAUTH2_TOKEN = 'fetch_oauth2_token'
OPERATION_FETCH_DATA = 'fetch_data'

STATUS_SUCCEEDED = 'succeeded'
STATUS_FAILED = 'failed'

FETCHER_NAME = 'OpalOAuth2HttpFetcher'

FETCH_OPERATIONS_TOTAL = f'{METRIC_NAMESPACE}_operations_total'
FETCH_OPERATION_DURATION_SECONDS = f'{METRIC_NAMESPACE}_operation_duration_seconds'
FETCH_RESPONSE_SIZE_BYTES = f'{METRIC_NAMESPACE}_response_size_bytes'
FETCH_IN_PROGRESS_OPERATIONS = f'{METRIC_NAMESPACE}_in_progress_operations'

FETCH_COUNTER = Counter(
    FETCH_OPERATIONS_TOTAL,
    'Total number of OAuth2 HTTP fetch operations',
    ['operation', 'status', 'http_status']
)

FETCH_OPERATION_DURATION = Histogram(
    FETCH_OPERATION_DURATION_SECONDS,
    'Duration of OAuth2 HTTP fetch operations in seconds',
    ['operation']
)

RESPONSE_SIZE_HISTOGRAM = Histogram(
    FETCH_RESPONSE_SIZE_BYTES,
    'Size of HTTP responses in bytes',
    ['operation']
)

IN_PROGRESS_OPERATIONS = Gauge(
    FETCH_IN_PROGRESS_OPERATIONS,
    'Number of OAuth2 HTTP fetch operations in progress',
    ['operation']
)

class OpalOAuth2HttpFetcherConfig(FetcherConfig):
    fetcher: str = "OpalOAuth2HttpFetcher"
    token_url: str
    client_id: str
    data_source_name: str
    scope: Optional[str] = None

class OpalOAuth2HttpFetchEvent(FetchEvent):
    fetcher: str = "OpalOAuth2HttpFetcher"
    config: OpalOAuth2HttpFetcherConfig = None

class OpalOAuth2HttpFetcher(BaseFetchProvider):
    def __init__(self, event: OpalOAuth2HttpFetchEvent) -> None:
        if event.config is None:
            event.config = OpalOAuth2HttpFetcherConfig()
        super().__init__(event)
        self.token = None

    def parse_event(self, event: FetchEvent) -> OpalOAuth2HttpFetchEvent:
        return OpalOAuth2HttpFetchEvent(**event.dict(exclude={"config"}), config=event.config)

    async def __aenter__(self):
        self.token = self.fetch_oauth2_token()
        return self

    async def __aexit__(self, exc_type=None, exc_val=None, tb=None):
        pass

    def fetch_oauth2_token(self):
        operation = OPERATION_FETCH_OAUTH2_TOKEN
        IN_PROGRESS_OPERATIONS.labels(operation=operation).inc()
        env_var_key = f"{self._event.config.data_source_name}_OAUTH_CLIENT_SECRET"

        client_secret = os.getenv(env_var_key, '')
        if not client_secret:
            error_message = f"Environment variable {env_var_key} not set"
            logger.error("Failed to fetch OAuth2 token: %s", error_message)
            FETCH_COUNTER.labels(operation=operation, status=STATUS_FAILED, http_status='N/A').inc()
            IN_PROGRESS_OPERATIONS.labels(operation=operation).dec()
            raise ValueError(error_message)

        data = {
            'client_id': self._event.config.client_id,
            'client_secret': client_secret,
            'grant_type': 'client_credentials'
        }
        if self._event.config.scope:
            data['scope'] = self._event.config.scope

        try:
            with FETCH_OPERATION_DURATION.labels(operation=operation).time():
                response = requests.post(self._event.config.token_url, data=data)
                response.raise_for_status()
                token = response.json()['access_token']
                FETCH_COUNTER.labels(
                    operation=operation,
                    status=STATUS_SUCCEEDED,
                    http_status=str(response.status_code)
                ).inc()
                return token
        except requests.RequestException as e:
            http_status = str(getattr(e.response, 'status_code', 'N/A'))
            logger.error("Failed to fetch OAuth2 token: %s", e)
            FETCH_COUNTER.labels(
                operation=operation,
                status=STATUS_FAILED,
                http_status=http_status
            ).inc()
            raise
        finally:
            IN_PROGRESS_OPERATIONS.labels(operation=operation).dec()

    async def _fetch_(self):
        operation = OPERATION_FETCH_DATA
        IN_PROGRESS_OPERATIONS.labels(operation=operation).inc()
        headers = {
            'Authorization': f'Bearer {self.token}'
        }

        try:
            with FETCH_OPERATION_DURATION.labels(operation=operation).time():
                response = requests.get(self._event.url, headers=headers)
                response.raise_for_status()
                data = response.json()
                FETCH_COUNTER.labels(
                    operation=operation,
                    status=STATUS_SUCCEEDED,
                    http_status=str(response.status_code)
                ).inc()
                RESPONSE_SIZE_HISTOGRAM.labels(operation=operation).observe(len(response.content))
                return data
        except requests.RequestException as e:
            http_status = str(getattr(e.response, 'status_code', 'N/A'))
            logger.error("Failed to fetch data: %s", e)
            FETCH_COUNTER.labels(
                operation=operation,
                status=STATUS_FAILED,
                http_status=http_status
            ).inc()
            raise
        finally:
            IN_PROGRESS_OPERATIONS.labels(operation=operation).dec()

    async def _process_(self, data):
        return data

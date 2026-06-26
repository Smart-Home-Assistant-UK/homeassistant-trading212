from __future__ import annotations

import base64

import aiohttp

from .const import (
    API_ACCOUNT_SUMMARY,
    API_DIVIDENDS,
    API_INSTRUMENTS,
    API_ORDERS,
    API_PIES,
    API_POSITIONS,
)


class InvalidAPIKeyError(Exception):
    pass


class RateLimitExceededError(Exception):
    pass


class APIConnectionError(Exception):
    pass


class APIResponseError(Exception):
    pass


class Trading212Client:
    def __init__(
        self, session: aiohttp.ClientSession, api_key: str, base_url: str, api_secret: str | None = None
    ) -> None:
        self._session = session
        self._base_url = base_url
        if api_secret:
            encoded = base64.b64encode(f"{api_key}:{api_secret}".encode()).decode()
            self._auth_header = f"Basic {encoded}"
        else:
            self._auth_header = api_key

    async def _get(self, path: str, params: dict | None = None) -> dict | list:
        url = f"{self._base_url}{path}"
        headers = {"Authorization": self._auth_header, "Accept": "application/json"}
        try:
            async with self._session.get(
                url, headers=headers, params=params, timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status in (401, 403):
                    raise InvalidAPIKeyError(f"HTTP {resp.status}")
                if resp.status == 429:
                    raise RateLimitExceededError("Rate limit exceeded")
                if not resp.ok:
                    raise APIResponseError(f"HTTP {resp.status}")
                data = await resp.json()
                # Trading212 sometimes returns 200 with a business exception body
                if isinstance(data, dict) and data.get("context", {}).get("type") == "TooManyRequests":
                    raise RateLimitExceededError("Rate limit exceeded")
                return data
        except (InvalidAPIKeyError, RateLimitExceededError, APIResponseError):
            raise
        except aiohttp.ClientConnectionError as err:
            raise APIConnectionError(str(err)) from err
        except aiohttp.ClientError as err:
            raise APIResponseError(str(err)) from err

    async def get_account_summary(self) -> dict:
        return await self._get(API_ACCOUNT_SUMMARY)

    async def get_positions(self) -> list:
        return await self._get(API_POSITIONS)

    async def get_orders(self) -> list:
        return await self._get(API_ORDERS)

    async def get_dividends(self) -> dict:
        return await self._get(API_DIVIDENDS)

    async def get_instruments(self) -> list:
        return await self._get(API_INSTRUMENTS)

    async def get_pies(self) -> list:
        return await self._get(API_PIES)

    async def get_pie(self, pie_id: int) -> dict:
        return await self._get(f"{API_PIES}/{pie_id}")

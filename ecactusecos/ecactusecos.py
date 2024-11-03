# type: ignore
import asyncio
import aiohttp
import async_timeout
import time
from yarl import URL

from .const import (
    API_HOST_EU,
    AUTHENTICATION_PATH,
    ACTUALS_PATH,
    AUTH_ACCESS_TOKEN,
    CUSTOMER_OVERVIEW_PATH,
    DEVICE_LIST_PATH,
    AUTH_TOKEN_HEADER,
    DEFAULT_SOURCE_TYPES,
    DEVICE_ALIAS_NAME,
)

from .exceptions import (
    EcactusEcosConnectionException,
    EcactusEcosException,
    EcactusEcosUnauthenticatedException,
)


class EcactusEcos:
    """Client to connect with EcactusEcos"""

    def __init__(
        self,
        username: str,
        password: str,
        api_host: str = API_HOST_EU,
        api_scheme: str = "https",
        api_port: int = 443,
        request_timeout: int = 10,
        source_types=DEFAULT_SOURCE_TYPES,
    ):
        self.api_scheme = api_scheme
        self.api_host = api_host
        self.api_port = api_port
        self.request_timeout = request_timeout
        self.source_types = source_types

        self._username = username
        self._password = password
        self._customer_info = None
        self._auth_token = None
        self._devices = None
        self._sources = None

    async def authenticate(self) -> None:
        """Log in using username and password.

        If succesfull, the authentication is saved and is_authenticated() returns true
        """
        # Make sure all data is cleared
        self.invalidate_authentication()

        url = URL.build(
            scheme=self.api_scheme,
            host=self.api_host,
            port=self.api_port,
            path=AUTHENTICATION_PATH,
        )

        # auth request, password grant type
        data = {
            "email": self._username,
            "password": self._password,
        }

        return await self.request(
            "POST",
            url,
            data=data,
            callback=self._handle_authenticate_response,
        )

    async def _handle_authenticate_response(self, response, params):
        json = await response.json()
        self._auth_token = json["data"][AUTH_ACCESS_TOKEN]

    async def customer_overview(self):
        """Request the customer overview."""
        if not self.is_authenticated():
            raise EcactusEcosUnauthenticatedException("Authentication required")

        url = URL.build(
            scheme=self.api_scheme,
            host=self.api_host,
            port=self.api_port,
            path=CUSTOMER_OVERVIEW_PATH,
        )

        return await self.request(
            "GET", url, callback=self._handle_customer_overview_response
        )

    async def _handle_customer_overview_response(self, response, params):
        json = await response.json()
        self._customer_info = json["data"]

    async def device_overview(self):
        if not self.is_authenticated():
            raise EcactusEcosUnauthenticatedException("Authentication required")

        url = URL.build(
            scheme=self.api_scheme,
            host=self.api_host,
            port=self.api_port,
            path=DEVICE_LIST_PATH,
        )
        return await self.request(
            "GET", url, callback=self._handle_device_list_repsonse
        )

    async def _handle_device_list_repsonse(self, response, params):
        json = await response.json()
        self._devices = dict()
        for device in json["data"]:
            self._devices[device["deviceId"]] = device

    async def actuals(self):
        """Request the actual values of the sources of the types configured in this instance (source_types)."""
        if not self.is_authenticated():
            raise EcactusEcosUnauthenticatedException("Authentication required")

        if not self._devices:
            await self.device_overview()

        actuals = dict()
        for device_id in self.get_device_ids():
            url = URL.build(
                scheme=self.api_scheme,
                host=self.api_host,
                port=self.api_port,
                path=ACTUALS_PATH,
            )
            actuals[device_id] = await self.request(
                "POST",
                url,
                data={"deviceId": device_id},
                callback=self._handle_actuals_response,
            )
        return actuals

    async def current_measurements(self, deviceIds=None):
        """Wrapper method which returns the relevant actual values of sources.

        When required, this method attempts to authenticate."""
        try:
            if not self.is_authenticated():
                await self.authenticate()

            if not self._devices:
                await self.device_overview()

            actuals = await self.actuals()
            current_measurements = dict()

            # When we have multiple devices we return the sum
            for source_type in self.source_types:
                match source_type:
                    case "batterySoc":
                        current_measurements[source_type] = (
                            min(
                                actual[source_type]
                                for deviceId, actual in actuals.items()
                                if (deviceIds is None or deviceId in deviceIds)
                                and actual[source_type] != 0
                            )
                            * 100
                        )
                    case _:
                        current_measurements[source_type] = sum(
                            actual[source_type]
                            for deviceId, actual in actuals.items()
                            if deviceIds is None or deviceId in deviceIds
                        )
            # When no deviceIds are given we add all devices by alias
            if deviceIds is None:
                for source_type in self.source_types:
                    for deviceId, actual in actuals.items():
                        if (
                            self._devices[deviceId] is not None
                            and self._devices[deviceId][DEVICE_ALIAS_NAME] is not None
                        ):
                            match source_type:
                                case "batterySoc":
                                    current_measurements[
                                        f"{self._devices[deviceId][DEVICE_ALIAS_NAME].lower()}{source_type[:1].upper() + source_type[1:]}"
                                    ] = actual[source_type] * 100
                                case _:
                                    current_measurements[
                                        f"{self._devices[deviceId][DEVICE_ALIAS_NAME].lower()}{source_type[:1].upper() + source_type[1:]}"
                                    ] = actual[source_type]
            return current_measurements

        except EcactusEcosUnauthenticatedException as exception:
            self.invalidate_authentication()
            raise exception

    async def _handle_actuals_response(self, response, params):
        json = await response.json()
        return json["data"]

    async def request(
        self,
        method: str,
        url: URL,
        data: dict = None,
        callback=None,
        params: dict = None,
    ):
        headers = {}
        json: dict = {
            **{
                "_t": int(time.time()),
                "clientType": "BROWSER",
                "clientVersion": "1.0",
            },
            **(data if data else {}),
        }

        # Insert authentication
        if self._auth_token is not None:
            headers[AUTH_TOKEN_HEADER] = "Bearer %s" % self._auth_token
        try:
            async with async_timeout.timeout(self.request_timeout):
                async with aiohttp.ClientSession() as session:
                    req = session.request(
                        method,
                        url,
                        json=json,
                        headers=headers,
                    )
                    async with req as response:
                        status = response.status
                        is_json = "application/json" in response.headers.get(
                            "Content-Type", ""
                        )

                        if (status == 401) or (status == 403):
                            raise EcactusEcosUnauthenticatedException(
                                await response.text()
                            )

                        if not is_json:
                            raise EcactusEcosException(
                                "Response is not json", await response.text()
                            )

                        if not is_json or (status // 100) in [4, 5]:
                            raise EcactusEcosException(
                                "Response is not success",
                                response.status,
                                await response.text(),
                            )

                        if callback is not None:
                            return await callback(response, params)

        except asyncio.TimeoutError as exception:
            raise EcactusEcosConnectionException(
                "Timeout occurred while communicating with EcactusEcos"
            ) from exception
        except aiohttp.ClientError as exception:
            raise EcactusEcosConnectionException(
                "Error occurred while communicating with EcactusEcos"
            ) from exception

    def is_authenticated(self):
        """Returns whether this instance is authenticated

        Note: despite this method returning true, requests could still fail to an authentication error."""
        return self._auth_token is not None

    def get_customer_info(self):
        """Returns the unique id of the currently authenticated user"""
        return self._customer_info

    def invalidate_authentication(self):
        """Invalidate the current authentication tokens and account details."""
        self._customer_info = None
        self._devices = None
        self._sources = None
        self._auth_token = None

    def get_device(self, device_id):
        """Gets the id of the device which belongs to the given source type, if present."""
        return (
            self._devices[device_id]
            if self._devices is not None and device_id in self._devices
            else None
        )

    def get_device_ids(self):
        """Gets the ids of the devices, if present."""
        return list(self._devices.keys()) if self._devices is not None else None

    def get_source_ids(self):
        """Gets the ids of the sources which belong to self.source_types, if present."""
        return [
            source_id
            for source_id in map(self.get_source_id, self.source_types)
            if source_id is not None
        ]

    def get_source_id(self, source_type):
        """Gets the id of the source which belongs to the given source type, if present."""
        return (
            self._sources[source_type]
            if self._sources is not None and source_type in self._sources
            else None
        )

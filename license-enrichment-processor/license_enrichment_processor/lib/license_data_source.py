from abc import ABC, abstractmethod
from lxml import html
from collections.abc import Awaitable
from logging import Logger
import urllib
import yarl
import asyncio
import aiohttp
from .sbom import ComponentLicenseDetails, Component


RetrieveLicenseError = Exception
RetrieveLicenseResult = ComponentLicenseDetails | None | RetrieveLicenseError


class LicenseDataSource(ABC):

    SOURCE_NAME: str

    @abstractmethod
    def retrieve(self, component: Component) -> Awaitable[RetrieveLicenseResult]:
        pass


class LicenseDataSourceSnyk(LicenseDataSource):

    _FETCH_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    }
    SOURCE_NAME: str = "SNYK"

    clientSession: aiohttp.ClientSession
    request_semaphore: asyncio.Semaphore
    logger: Logger

    def __init__(
        self,
        clientSession: aiohttp.ClientSession,
        logger: Logger,
        request_limit_per_second: int = 1,
    ) -> None:
        self.clientSession = clientSession
        self.logger = logger
        self.request_semaphore = asyncio.Semaphore(request_limit_per_second)

    async def retrieve(self, component: Component) -> RetrieveLicenseResult:
        async with self.request_semaphore:
            url = self._create_snyk_url(component)
            self.logger.info(
                f"Retrieving license details from Snyk: {url}", extra={"url": url}
            )
            try:
                result = await self._fetch(url)
            except Exception as e:
                self.logger.error(
                    f"Retrieving license details from Snyk failed: {url}",
                    exc_info=True,
                    extra={"url": url},
                )
                return e
            await asyncio.sleep(1)
            return result

    async def _fetch(self, url: yarl.URL) -> ComponentLicenseDetails | None:
        async with self.clientSession.get(url, headers=self._FETCH_HEADERS) as response:
            if response.status == 404:
                return None

            if response.status != 200:
                raise Exception()

            content = await response.text()
            tree = html.fromstring(content)
            license_expr = tree.xpath(
                '//span[@data-snyk-test="license item list: spdx license expression"]'
            )[0].text_content()
            if license_expr[0] == "(":
                license_expr = license_expr[1:]
            if license_expr[-1] == ")":
                license_expr = license_expr[:-1]

            return (
                None
                if license_expr == "Unknown"
                else ComponentLicenseDetails(
                    license_expressions=[(license_expr, self.SOURCE_NAME)]
                )
            )

    def _create_snyk_url(self, component: Component) -> yarl.URL:
        identifier = (
            f"{component.org}%3A{component.name}"
            if component.package_manager == "maven"
            else (
                f"{component.org.replace('@', '%40')}%2F{component.name}"
                if component.package_manager and component.org != ""
                else component.name
            )
        )
        return yarl.URL(
            f"https://security.snyk.io/package/{component.package_manager}/{identifier}/{component.version}",
            encoded=True,
        )


class LicenseDataSourceClearlyDefined(LicenseDataSource):

    SOURCE_NAME: str = "CLEARLY_DEFINED"
    clientSession: aiohttp.ClientSession
    request_semaphore: asyncio.Semaphore
    logger: Logger

    def __init__(
        self,
        clientSession: aiohttp.ClientSession,
        logger: Logger,
        request_limit_per_second: int = 4,
    ) -> None:
        self.clientSession = clientSession
        self.logger = logger
        self.request_semaphore = asyncio.Semaphore(request_limit_per_second)

    async def retrieve(self, component: Component) -> RetrieveLicenseResult:
        async with self.request_semaphore:
            url = self._create_clearlydefined_url(component)
            self.logger.info(
                f"Retrieving license details from ClearlyDefined: {url}",
                extra={"url": url},
            )
            try:
                result = await self._fetch(url)
            except Exception as e:
                self.logger.error(
                    f"Retrieving license details from ClearlyDefined failed: {url}",
                    exc_info=True,
                    extra={"url": url},
                )
                return e
            await asyncio.sleep(1)
            return result

    async def _fetch(self, url: str) -> ComponentLicenseDetails | None:
        async with self.clientSession.get(url) as response:
            if response.status == 404:
                return None
            if response.status != 200:
                raise Exception()

            content = await response.json()
            declared_license, license_expressions, attributions, source_url = (
                self.try_index_key(content, "licensed", "declared"),
                self.try_index_key(
                    content, "licensed", "facets", "core", "discovered", "expressions"
                ),
                self.try_index_key(
                    content, "licensed", "facets", "core", "attribution", "parties"
                ),
                self.try_index_key(content, "described", "sourceLocation", "url"),
            )
            license_expressions = (
                [(declared_license, "ClearlyDefined Declared")]
                if type(declared_license) == str
                else []
            ) + (
                [(expr, "ClearlyDefined Discovered") for expr in license_expressions]
                if type(license_expressions) == list
                else []
            )
            attributions = (
                []
                if not type(attributions) == list
                else [(attr, "ClearlyDefined Discovered") for attr in attributions]
            )
            source_urls = (
                []
                if not type(source_url) == str
                else [(source_url, "ClearlyDefined Discovered")]
            )

            return (
                None
                if all(
                    [
                        len(license_expressions) == 0,
                        len(attributions) == 0,
                        len(source_urls) == 0,
                    ]
                )
                else ComponentLicenseDetails(
                    license_expressions=license_expressions,
                    attributions=attributions,
                    source_urls=source_urls,
                )
            )

    def _create_clearlydefined_url(self, component: Component):
        providers: dict[str, str] = {"maven": "mavencentral", "npm": "npmjs"}
        return "/".join(
            [
                "https://api.clearlydefined.io/definitions",
                *[
                    urllib.parse.quote(it, safe=[])
                    for it in [
                        component.purl.type,
                        providers[component.purl.type],
                        (
                            component.purl.namespace
                            if component.purl.namespace != ""
                            else "-"
                        ),
                        component.purl.name,
                        component.purl.version,
                    ]
                ],
            ]
        )

    def try_index_key(self, obj, *path, default=None):
        res = obj
        for key in path:
            if key in res:
                res = res[key]
            else:
                return default
        return res

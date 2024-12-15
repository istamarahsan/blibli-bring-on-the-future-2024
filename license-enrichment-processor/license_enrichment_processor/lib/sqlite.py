from sqlite3 import Connection, Cursor
from typing import Callable
from packageurl import PackageURL
from .sbom import Component, ComponentLicenseDetails
from .date import DatetimeProvider

ConnectionFactory = Callable[[], Connection]


class SqliteDatabase:

    connection_factory: ConnectionFactory
    datetime_provider: DatetimeProvider

    def __init__(
        self, connection_factory: ConnectionFactory, datetime_provider: DatetimeProvider
    ):
        self.connection_factory = connection_factory
        self.datetime_provider = datetime_provider

    def get_components(
        self, purls: list[PackageURL]
    ) -> dict[PackageURL, ComponentLicenseDetails]:
        cursor = self.connection_factory().cursor()
        results = [
            (purl, self._get_component(purl.to_string(), cursor)) for purl in purls
        ]
        return {purl: result for purl, result in results if result is not None}

    def cache_components(self, components: list[Component]) -> None:
        now = self.datetime_provider.now()
        cursor = self.connection_factory().cursor()

        for component in components:
            cursor.execute(
                """
                INSERT OR REPLACE INTO component (purl, updatedAt)
                VALUES (?, ?)
                """,
                (
                    component.purl.to_string(),
                    now.isoformat(),
                ),
            )
            cursor.executemany(
                """
                INSERT OR REPLACE INTO component_license_expression (componentPurl, expression, source)
                VALUES (?, ?, ?)
                """,
                [
                    (component.purl.to_string(), expression, source)
                    for expression, source in component.license_details.license_expressions
                ],
            )

            cursor.executemany(
                """
                INSERT OR REPLACE INTO component_attribution (componentPurl, attribution, source)
                VALUES (?, ?, ?)
                """,
                [
                    (component.purl.to_string(), attribution, source)
                    for attribution, source in component.license_details.attributions
                ],
            )

            cursor.executemany(
                """
                INSERT OR REPLACE INTO component_source_code_url (componentPurl, sourceCodeUrl, source)
                VALUES (?, ?, ?)
                """,
                [
                    (component.purl.to_string(), url, source)
                    for url, source in component.license_details.source_urls
                ],
            )

        cursor.connection.commit()

    def _get_component(
        self, purl: str, cursor: Cursor
    ) -> ComponentLicenseDetails | None:
        cursor.execute(
            """
            SELECT purl
            FROM component
            WHERE purl = ?
            """,
            (purl,),
        )
        result = cursor.fetchone()
        if result is None:
            return None

        cursor.execute(
            """
            SELECT expression, source
            FROM component_license_expression
            WHERE componentPurl = ?
            """,
            (purl,),
        )
        expressions = cursor.fetchall()

        cursor.execute(
            """
            SELECT attribution, source
            FROM component_attribution
            WHERE componentPurl = ?
            """,
            (purl,),
        )
        attributions = cursor.fetchall()

        cursor.execute(
            """
            SELECT sourceCodeUrl, source
            FROM component_source_code_url
            WHERE componentPurl = ?
            """,
            (purl,),
        )
        source_urls = cursor.fetchall()

        return ComponentLicenseDetails(
            license_expressions=expressions,
            attributions=attributions,
            source_urls=source_urls,
        )

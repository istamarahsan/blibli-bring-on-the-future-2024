from dataclasses import dataclass
import dataclasses
import datetime
import asyncio
from logging import Logger
from .dependency_track import DependencyTrack
from .components_cache import ComponentsCache
from .retry_memory import RetryMemory
from .sbom import Component, ComponentLicenseDetails
from .date import DatetimeProvider
from .license_data_source import LicenseDataSource
from packageurl import PackageURL


@dataclass
class BomProcessedEvent:
    @dataclass
    class Project:
        uuid: str
        name: str
        version: str
        purl: str | None = None

    timestamp: datetime.datetime
    content: str
    project: Project


class LicenseEnrichmentProcessor:
    dependency_track: DependencyTrack
    components_cache: ComponentsCache
    retry_memory: RetryMemory
    datetime_provider: DatetimeProvider
    license_data_source: LicenseDataSource
    fetch_cooldown: datetime.timedelta
    logger: Logger

    def __init__(
        self,
        dependency_track: DependencyTrack,
        components_cache: ComponentsCache,
        retry_memory: RetryMemory,
        license_data_source: LicenseDataSource,
        datetime_provider: DatetimeProvider,
        fetch_cooldown: datetime.timedelta,
        logger: Logger,
    ):
        self.dependency_track = dependency_track
        self.components_cache = components_cache
        self.retry_memory = retry_memory
        self.datetime_provider = datetime_provider
        self.fetch_cooldown = fetch_cooldown
        self.license_data_source = license_data_source
        self.logger = logger

    async def enrich_from_bom_processed_event(self, event: BomProcessedEvent):
        datetime_enrichment_started = self.datetime_provider.now()
        self.logger.info(f"Enriching from event: {event.content}")
        project_components = await self.dependency_track.get_components(
            event.project.uuid
        )
        self.logger.info(
            f"Found {len(project_components)} components for project '{event.project.name}'"
        )
        project_components_with_purl = [
            component for component in project_components if component.purl
        ]
        self.logger.info(
            f"{len(project_components_with_purl)}/{len(project_components)} have PURLs and can be processed"
        )
        project_components_with_purl_by_purl = {
            component.purl: component
            for component in project_components
            if component.purl
        }
        cached_license_details = self.components_cache.get_components(
            [component.purl for component in project_components_with_purl]
        )
        self.logger.info(
            f"Using cache for {len(cached_license_details)}/{len(project_components_with_purl)} components"
        )
        components_not_in_cache = [
            component
            for component in project_components_with_purl
            if component.purl not in cached_license_details
        ]
        retry_memories: dict[PackageURL, datetime.datetime | None] = {
            component.purl: self.retry_memory.recall(component.purl)
            for component in components_not_in_cache
        }

        components_to_fetch = [
            component
            for component in components_not_in_cache
            if retry_memories[component.purl] is None
            or retry_memories[component.purl] - datetime_enrichment_started
            > self.fetch_cooldown
        ]
        self.logger.info(
            f"{len(components_to_fetch)}/{len(components_not_in_cache)} missing components are not on cooldown and will be fetched"
        )

        async def fetch_component(component: Component):
            result = await self.license_data_source.retrieve(component)
            return component.purl, result

        fetch_components_result = await asyncio.gather(
            *[fetch_component(component) for component in components_to_fetch]
        )

        failed_results: list[PackageURL] = [
            purl
            for purl, result in fetch_components_result
            if not isinstance(result, ComponentLicenseDetails)
        ]
        for purl in failed_results:
            self.retry_memory.remember(purl, datetime_enrichment_started)

        successful_results: list[tuple[PackageURL, ComponentLicenseDetails]] = [
            (purl, result)
            for purl, result in fetch_components_result
            if isinstance(result, ComponentLicenseDetails)
        ]
        self.logger.info(
            f"License data for {len(successful_results)}/{len(components_to_fetch)} components successfully fetched"
        )

        enriched_components = [
            dataclasses.replace(
                project_components_with_purl_by_purl[purl],
                license_details=license_details_result,
            )
            for purl, license_details_result in successful_results
        ]
        self.components_cache.cache_components(enriched_components)

        components_to_update = [
            *[
                dataclasses.replace(
                    project_components_with_purl_by_purl[purl],
                    license_details=license_details,
                )
                for purl, license_details in cached_license_details.items()
            ],
            *enriched_components,
        ]

        await asyncio.gather(
            *[
                self.dependency_track.update_component_license_expression(
                    component.uuid,
                    self._select_license_expression(component.license_details),
                )
                for component in components_to_update
                if len(component.license_details.license_expressions) > 0
            ]
        )
        self.logger.info(
            f"Updated {len(components_to_update)} components in project '{event.project.name}'"
        )

    SOURCE_PRIORITY_ORDER = {
        source_name: i
        for i, source_name in enumerate(
            reversed(["Snyk", "ClearlyDefined Declared", "ClearlyDefined Discovered"])
        )
    }

    def _select_license_expression(
        self, license_details: ComponentLicenseDetails
    ) -> str | None:
        def sort_key(license_expr_with_source: tuple[str, str]) -> tuple[int, int]:
            expr, source = license_expr_with_source
            return (
                (
                    self.SOURCE_PRIORITY_ORDER[source]
                    if source in self.SOURCE_PRIORITY_ORDER
                    else -1
                ),
                len(expr),
            )

        return max(license_details.license_expressions, key=sort_key, default=None)[0]

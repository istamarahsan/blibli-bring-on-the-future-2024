from .sbom import Component, ComponentLicenseDetails
from packageurl import PackageURL
from typing import Protocol


class ComponentsCache(Protocol):
    def get_components(
        self, purls: list[PackageURL]
    ) -> dict[PackageURL, ComponentLicenseDetails]:
        pass

    def cache_components(self, components: list[Component]) -> None:
        pass

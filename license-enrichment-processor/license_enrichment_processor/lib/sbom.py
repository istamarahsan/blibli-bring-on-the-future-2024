from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from packageurl import PackageURL
import copy

LicenseExpressionWithSource = tuple[str, str]
AttributionWithSource = tuple[str, str]
SourceUrlWithSource = tuple[str, str]


@dataclass
class ComponentLicenseDetails:
    license_expressions: list[LicenseExpressionWithSource] = field(default_factory=list)
    attributions: list[AttributionWithSource] = field(default_factory=list)
    source_urls: list[SourceUrlWithSource] = field(default_factory=list)

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.equals(other)

    def equals(self, other: "ComponentLicenseDetails") -> bool:
        return (
            set(self.license_expressions) == set(other.license_expressions)
            and set(self.attributions) == set(other.attributions)
            and set(self.source_urls) == set(other.source_urls)
        )

    def to_dict(self) -> dict:
        return {
            "licenseExpressions": [
                {"expression": exp, "source": source}
                for exp, source in self.license_expressions
            ],
            "attributions": [
                {"attribution": attr, "source": source}
                for attr, source in self.attributions
            ],
            "sourceUrls": [
                {"url": url, "source": source} for url, source in self.source_urls
            ],
        }

    @staticmethod
    def from_dict(dict: dict) -> "ComponentLicenseDetails":
        return ComponentLicenseDetails(
            license_expressions=[
                (it["expression"], it["source"]) for it in dict["licenseExpressions"]
            ],
            attributions=[
                (it["attribution"], it["source"]) for it in dict["attributions"]
            ],
            source_urls=[(it["url"], it["source"]) for it in dict["sourceUrls"]],
        )

    def present_sources(self) -> set[str]:
        return {
            source
            for _, source in [
                *self.license_expressions,
                *self.attributions,
                *self.source_urls,
            ]
        }

    def is_empty(self) -> bool:
        return (
            len(self.license_expressions) == 0
            and len(self.attributions) == 0
            and len(self.source_urls) == 0
        )

    def merge(self, other: "ComponentLicenseDetails") -> "ComponentLicenseDetails":
        return ComponentLicenseDetails(
            license_expressions=list(
                {
                    f"{exp}{source}": (exp, source)
                    for exp, source in [
                        *self.license_expressions,
                        *other.license_expressions,
                    ]
                }.values()
            ),
            attributions=list(
                {
                    f"{attr}{source}": (attr, source)
                    for attr, source in [*self.attributions, *other.attributions]
                }.values()
            ),
            source_urls=list(
                {
                    f"{url}{source}": (url, source)
                    for url, source in [*self.source_urls, *other.source_urls]
                }.values()
            ),
        )


@dataclass
class Component:
    uuid: str
    purl: PackageURL | None
    license_details: ComponentLicenseDetails

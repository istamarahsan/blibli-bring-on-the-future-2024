from .sbom import Component, ComponentLicenseDetails
from aiohttp import ClientSession
import yarl
import itertools
from packageurl import PackageURL


class DependencyTrack:

    client: ClientSession
    api_url: str
    api_key: str

    json_headers = {"Content-Type": "application/json"}

    def __init__(self, client: ClientSession, api_url: str, api_key: str):
        self.client = client
        self.api_url = api_url
        self.api_key = api_key

    async def get_components(self, project_uuid: str) -> list[Component]:
        def parse_component(data: dict) -> Component:
            existing_license_expression: str | None = (
                data["resolvedLicense"]["licenseId"]
                if "resolvedLicense" in data
                else data["licenseExpression"] if "licenseExpression" in data else None
            )
            return Component(
                uuid=data["uuid"],
                purl=PackageURL.from_string(data["purl"]) if "purl" in data else None,
                license_details=ComponentLicenseDetails(
                    license_expressions=(
                        [(existing_license_expression, "DependencyTrack")]
                        if existing_license_expression
                        else []
                    )
                ),
            )

        url = yarl.URL(f"{self.api_url}/api/v1/component/project/{project_uuid}")
        result: list[Component] = []
        for pageNumber in itertools.count(start=1):
            response = await self.client.get(
                url,
                headers=self._auth_headers(),
                params={"pageSize": 100, "pageNumber": pageNumber},
            )
            data = await response.json()
            if len(data) == 0:
                break
            result = result + [parse_component(it) for it in data]
        return result

    async def update_component_license_expression(
        self, component_uuid: str, license_expression: str
    ) -> None:
        get_url = yarl.URL(f"{self.api_url}/api/v1/component/{component_uuid}")
        get_license_url = yarl.URL(
            f"{self.api_url}/api/v1/license/{license_expression}"
        )
        post_url = yarl.URL(f"{self.api_url}/api/v1/component")

        get_response = await self.client.get(get_url, headers=self._auth_headers())
        component_payload: dict = await get_response.json()

        component_payload.pop("licenseExpression", None)
        component_payload.pop("licenseUrl", None)
        component_payload.pop("resolvedLicense", None)

        get_license_response = await self.client.get(
            get_license_url, headers=self._auth_headers()
        )
        resolved_license: dict | None = (
            (await get_license_response.json())
            if get_license_response.status == 200
            else None
        )
        if resolved_license:
            component_payload["license"] = resolved_license["licenseId"]
        else:
            component_payload["licenseExpression"] = license_expression
        await self.client.post(
            post_url,
            headers=self._auth_headers() | self.json_headers,
            json=component_payload,
        )

    def _auth_headers(self) -> dict[str, str]:
        return {"X-API-Key": self.api_key}

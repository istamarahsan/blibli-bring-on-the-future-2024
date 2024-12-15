from flask import Blueprint, request, abort
import jsonschema
import datetime
from .config import get_enrichment_processor
from .lib.license_enrichment_processor import (
    BomProcessedEvent,
)


def create_blueprint(
    url_prefix: str = "",
) -> Blueprint:
    blueprint = Blueprint("Router", __name__, url_prefix=url_prefix)

    @blueprint.post("/hook/bom-processed")
    async def post_bom_processed():
        payload = request.json
        try:
            jsonschema.validate(instance=payload, schema=bom_processed_payload_schema)
            as_event = parse_bom_processed_payload(payload)
            processor, client = get_enrichment_processor()
            await processor.enrich_from_bom_processed_event(as_event)
            await client.close()
            return ""
        except jsonschema.ValidationError as e:
            abort(400, e.message)

    return blueprint


def parse_bom_processed_payload(payload: dict) -> BomProcessedEvent:
    return BomProcessedEvent(
        timestamp=datetime.datetime.fromisoformat(payload["notification"]["timestamp"]),
        content=payload["notification"]["content"],
        project=BomProcessedEvent.Project(
            uuid=payload["notification"]["subject"]["project"]["uuid"],
            name=payload["notification"]["subject"]["project"]["name"],
            version=payload["notification"]["subject"]["project"]["version"],
            purl=(
                payload["notification"]["subject"]["project"]["purl"]
                if "purl" in payload["notification"]["subject"]["project"]
                else None
            ),
        ),
    )


bom_processed_payload_schema = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "notification": {
            "type": "object",
            "properties": {
                "level": {
                    "type": "string",
                    "enum": ["INFORMATIONAL", "WARNING", "ERROR"],
                },
                "scope": {"type": "string", "enum": ["PORTFOLIO"]},
                "group": {"type": "string", "enum": ["BOM_PROCESSED"]},
                "timestamp": {"type": "string", "format": "date-time"},
                "title": {"type": "string"},
                "content": {"type": "string"},
                "subject": {
                    "type": "object",
                    "properties": {
                        "project": {
                            "type": "object",
                            "properties": {
                                "uuid": {"type": "string", "format": "uuid"},
                                "name": {"type": "string"},
                                "version": {"type": "string"},
                                "purl": {"type": "string"},
                            },
                            "required": ["uuid", "name", "version"],
                        },
                        "bom": {
                            "type": "object",
                            "properties": {
                                "content": {"type": "string"},
                                "format": {
                                    "type": "string",
                                    "enum": ["CycloneDX"],
                                },
                                "specVersion": {"type": "string"},
                            },
                            "required": ["content", "format", "specVersion"],
                        },
                    },
                    "required": ["project", "bom"],
                },
            },
            "required": [
                "level",
                "scope",
                "group",
                "timestamp",
                "title",
                "content",
                "subject",
            ],
        }
    },
    "required": ["notification"],
}

import os
import sqlite3
import datetime
from aiohttp import ClientSession
import logging
from flask import current_app
from .lib.date import DatetimeProvider
from .lib.dependency_track import DependencyTrack
from .lib.sqlite import SqliteDatabase
from .lib.retry_memory import InMemoryRetryMemory
from .lib.license_enrichment_processor import LicenseEnrichmentProcessor
from .lib.license_data_source import LicenseDataSourceClearlyDefined

config = {
    "DEPENDENCY_TRACK_API_URL": os.environ["DEPENDENCY_TRACK_API_URL"],
    "DEPENDENCY_TRACK_API_KEY": os.environ["DEPENDENCY_TRACK_API_KEY"],
    "DB_PATH": os.environ["DB_PATH"],
}


def get_enrichment_processor() -> tuple[LicenseEnrichmentProcessor, ClientSession]:
    logger = current_app.logger
    datetime_provider = DatetimeProvider.FromOffsetHours(7)
    client_session = ClientSession()
    dependency_track = DependencyTrack(
        client=client_session,
        api_url=config["DEPENDENCY_TRACK_API_URL"],
        api_key=config["DEPENDENCY_TRACK_API_KEY"],
    )
    components_cache = SqliteDatabase(
        connection_factory=lambda: sqlite3.connect(config["DB_PATH"]),
        datetime_provider=datetime_provider,
    )
    retry_memory = InMemoryRetryMemory()
    license_data_source = LicenseDataSourceClearlyDefined(
        clientSession=client_session, logger=logger, request_limit_per_second=5
    )
    fetch_cooldown = datetime.timedelta(days=30)
    enrichment_processor = LicenseEnrichmentProcessor(
        dependency_track=dependency_track,
        components_cache=components_cache,
        retry_memory=retry_memory,
        license_data_source=license_data_source,
        datetime_provider=datetime_provider,
        fetch_cooldown=fetch_cooldown,
        logger=logger,
    )
    return enrichment_processor, client_session

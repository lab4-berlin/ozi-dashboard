"""Async variants of the ETL job helpers used for ASN neighbours.

The async client (``extract_from_ripe_api_async``) handles the connection pool,
retries, and 429 backoff. This module owns the per-job orchestration: walking
the date list, fanning out neighbour requests with ``asyncio.as_completed``,
and yielding completed batches so the caller can hand them off to the
(synchronous) DB layer.
"""

import asyncio
from typing import AsyncIterator, List

from etl_jobs import display_progress
from extract_from_ripe_api_async import (
    get_asn_neighbours,
    get_country_asns,
)


def _parse_asn_list(payload: dict, date) -> List[dict]:
    if not payload or not payload.get("data") or not payload["data"].get("countries"):
        return []
    country_block = payload["data"]["countries"][0]
    routed_asns = country_block.get("routed", "")
    non_routed_asns = country_block.get("non_routed", "")
    routed_list = [
        item.split("(")[1].split(")")[0]
        for item in routed_asns.strip("{}").split(", ")
        if item.startswith("AsnSingle")
    ]
    non_routed_list = [
        item.split("(")[1].split(")")[0]
        for item in non_routed_asns.strip("{}").split(", ")
        if item.startswith("AsnSingle")
    ]

    out: List[dict] = []
    date_str = date.strftime("%Y-%m-%d")
    for asn in routed_list:
        out.append({"asn": asn, "date": date_str, "is_routed": True})
    for asn in non_routed_list:
        out.append({"asn": asn, "date": date_str, "is_routed": False})
    return out


async def get_list_of_asns_for_country_async(
    country_iso2, dates, batch_size, verbose=True
) -> AsyncIterator[List[dict]]:
    total_number_of_dates = len(dates)
    asns_batch: List[dict] = []
    received_from_api = 0

    if verbose and dates:
        display_progress(0, total_number_of_dates, dates[0], 0, 0)

    remaining = list(dates)
    processed = 0
    while remaining:
        date = remaining.pop(0)
        d = await get_country_asns(country_iso2, date)
        for entry in _parse_asn_list(d or {}, date):
            asns_batch.append(entry)

        processed += 1
        if verbose:
            display_progress(
                processed - 1,
                total_number_of_dates,
                date,
                received_from_api + len(asns_batch),
                received_from_api,
            )

        if len(asns_batch) >= batch_size:
            yield asns_batch
            received_from_api += len(asns_batch)
            asns_batch = []

    if asns_batch:
        yield asns_batch


async def _fetch_neighbours_one(asn, date):
    data = await get_asn_neighbours(asn, date)
    return asn, data


async def get_list_of_asn_neighbours_for_country_async(
    country_iso2, dates, batch_size, verbose=True
) -> AsyncIterator[List[dict]]:
    """Async generator mirroring ``etl_jobs.get_list_of_asn_neighbours_for_country``.

    Per date: fetch the ASN list once, then fan out one neighbour request per
    ASN. Concurrency is bounded by the client-side semaphore + connection pool
    in ``extract_from_ripe_api_async``. Completed neighbour responses are
    appended to the running batch and yielded as soon as ``batch_size`` is
    reached, so the caller can write to the DB while later requests are still
    in flight.
    """
    total_number_of_dates = len(dates)
    neighbours_batch: List[dict] = []
    received_from_api = 0
    stored_to_database = 0

    if verbose and dates:
        display_progress(0, total_number_of_dates, dates[0], 0, 0)

    remaining = list(dates)
    while remaining:
        date = remaining.pop(0)
        date_str = date.strftime("%Y-%m-%d")

        async for asn_list in get_list_of_asns_for_country_async(
            country_iso2, [date], batch_size, verbose=False
        ):
            if not asn_list:
                continue

            tasks = [
                asyncio.create_task(_fetch_neighbours_one(item["asn"], date))
                for item in asn_list
            ]

            counter = 0
            total = len(tasks)
            try:
                for coro in asyncio.as_completed(tasks):
                    asn, d = await coro
                    counter += 1

                    if verbose:
                        display_progress(
                            total_number_of_dates - len(remaining) - 1,
                            total_number_of_dates,
                            date,
                            received_from_api + len(neighbours_batch),
                            stored_to_database,
                            f"    asn {counter}/{total}",
                        )

                    if d and d.get("data") and d["data"].get("neighbours"):
                        for row in d["data"]["neighbours"]:
                            row["asn_req"] = asn
                            row["date"] = date_str
                            neighbours_batch.append(row)

                    if len(neighbours_batch) >= batch_size:
                        yield neighbours_batch
                        stored_to_database += len(neighbours_batch)
                        received_from_api += len(neighbours_batch)
                        neighbours_batch = []
            except BaseException:
                for t in tasks:
                    if not t.done():
                        t.cancel()
                raise

    if neighbours_batch:
        yield neighbours_batch

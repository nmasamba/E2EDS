"""Seeded synthetic operations data (../reference_workload.md); fictional and never committed."""

import csv
import random
from datetime import UTC, datetime, timedelta
from pathlib import Path

HEADER = (
    "order_id",
    "account_num",
    "created_at",
    "region",
    "item_count",
    "service_level",
    "quoted_transit_hours",
    "actual_transit_hours",
)
QUOTED = {"standard": 48, "express": 24}


def write_orders(path: Path, orders: int = 2000, accounts: int = 400, seed: int = 0) -> None:
    """Write the orders table: one row per order, string IDs with leading zeros, UTC timestamps."""
    rng = random.Random(seed)
    start = datetime(2026, 1, 1, tzinfo=UTC)
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(HEADER)
        for number in range(orders):
            level = rng.choice(list(QUOTED))
            writer.writerow(
                (
                    f"order-{number:06d}",
                    f"{number % accounts:06d}",
                    (start + timedelta(minutes=rng.randrange(300_000))).isoformat(),
                    rng.choice(("north", "south", "east", "west")),
                    rng.randint(1, 9),
                    level,
                    QUOTED[level],
                    round(QUOTED[level] * rng.uniform(0.6, 1.8), 1),
                )
            )

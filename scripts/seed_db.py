"""Seed a fresh database with initial dev data."""

import asyncio
import logging
import os
import sys
import time

from bonsai_api.cli.cli import create_group, create_user, setup
from bonsai_api.cli.utils import run_async
from bonsai_api.crud.group import get_groups
from bonsai_api.crud.user import get_users
from bonsai_api.db.db import MongoDatabase
from click.testing import CliRunner
from pymongo import AsyncMongoClient

LOG = logging.getLogger("seed_db")


async def get_users_from_db(db_uri: str, db_name: str):
    """Retrieve users from the database and close the client afterwards."""
    client = AsyncMongoClient(db_uri)
    try:
        db = MongoDatabase()
        db.setup(client, db_name=db_name)
        users = await get_users(db)
        return users
    finally:
        await client.close()


async def wait_for_db(db_uri: str, timeout: int = 30, interval: float = 1.0) -> bool:
    """Wait for MongoDB to become available by pinging it.

    Returns True if the DB responded before timeout, otherwise False.
    """
    deadline = time.time() + timeout
    client = AsyncMongoClient(db_uri)
    try:
        while True:
            try:
                # admin.command('ping') is a lightweight check
                await client.admin.command("ping")
                return True
            except Exception as exc:  # pragma: no cover - runtime network
                if time.time() > deadline:
                    LOG.error("Timed out waiting for MongoDB: %s", exc)
                    return False
                await asyncio.sleep(interval)
    finally:
        await client.close()


async def verify_seeded(
    db_uri: str,
    db_name: str,
    expected_usernames: list[str],
    expected_group_ids: list[str],
) -> bool:
    """Simple smoke test to verify that expected users and groups exist.

    Connects to the DB, queries users and groups and returns True if all
    expected items are present.
    """
    client = AsyncMongoClient(db_uri)
    try:
        db = MongoDatabase()
        db.setup(client, db_name=db_name)

        users = await get_users(db, usernames=expected_usernames)
        found_usernames = {u.username for u in users}
        for username in expected_usernames:
            if username not in found_usernames:
                LOG.error("Expected user not found: %s", username)
                return False

        groups = await get_groups(db)
        found_group_ids = {g.group_id for g in groups}
        for gid in expected_group_ids:
            if gid not in found_group_ids:
                LOG.error("Expected group not found: %s", gid)
                return False

        return True
    finally:
        await client.close()


def seed(db_uri: str):
    """Seed the database with initial data if no users exist."""
    # check if users exist
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s: %(message)s",
    )

    LOG.info("Waiting for MongoDB at %s", db_uri)
    ok = run_async(wait_for_db(db_uri, timeout=30))
    if not ok:
        LOG.error("Database not available, aborting seed.")
        sys.exit(1)

    users = run_async(get_users_from_db(db_uri, "bonsai"))
    if users:
        LOG.info("Database already seeded with users, skipping...")
        return

    # Setup click CLI execution
    runner = CliRunner()
    with runner.isolated_filesystem():
        LOG.info("Bootstrapping bonsai database...")
        out = runner.invoke(setup)

        if out.exit_code != 0:
            LOG.error("Error during setup:\n%s", out.output)
            sys.exit(1)

        LOG.info("Creating users...")
        for username, pwd, email, role in [
            ("user", "user", "user@mail.com", "user"),
        ]:
            out = runner.invoke(
                create_user,
                [
                    "--username",
                    username,
                    "--password",
                    pwd,
                    "--email",
                    email,
                    "--role",
                    role,
                ],
            )
            if out.exit_code != 0:
                LOG.error("Error creating user %s:\n%s", username, out.output)
                sys.exit(1)
            LOG.info("Created user: %s", username)

    # Create groups
    for gid, display_name, description in [
        ("mtuberculosis", "M. tuberculosis", "Tuberculosis test samples"),
        ("saureus", "S. aureus", "MRSA test samples"),
        ("ecoli", "E. coli", "E. coli test samples"),
        ("streptococcus", "Streptococcus spp", "S. pyogenes test samples"),
    ]:
        out = runner.invoke(
            create_group,
            [
                "--id",
                gid,
                "--name",
                display_name,
                "--description",
                description,
            ],
        )
        if out.exit_code != 0:
            LOG.error("Error creating group %s:\n%s", gid, out.output)
            sys.exit(1)
        LOG.info("Created group: %s", gid)

    LOG.info("Seeding complete.")


if __name__ == "__main__":
    uri = os.getenv("MONGODB_URI", "mongodb://mongodb:27017?replicaSet=rs0")

    seed(uri)

    # Run smoke tests to verify that db was seed
    LOG.info("Verifying seeded data...")
    ok = run_async(
        verify_seeded(
            uri,
            "bonsai",
            expected_usernames=["admin", "user"],
            expected_group_ids=[
                "mtuberculosis",
                "saureus",
                "ecoli",
                "streptococcus",
            ],
        )
    )
    if not ok:
        LOG.error("Smoke test failed: seeded data not found")
        sys.exit(1)
    LOG.info("Smoke test passed: users and groups present")

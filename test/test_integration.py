"""
This module contains an integration test for the Infernet Router API.

It assumes that:
1. The router is deployed at infernet-router.ritual.net
2. At least 10 *reachable* nodes are running the hello-world container
"""

import asyncio
import random

import pytest
from aiohttp import ClientSession

ROUTER_URL = "http://infernet-router.ritual.net"


@pytest.mark.asyncio
async def test_integration() -> None:
    print("\n")

    async with ClientSession() as session:
        # Get available containers (services)
        containers_url = f"{ROUTER_URL}/api/v1/containers"
        async with session.get(containers_url) as response:
            assert response.status == 200
            containers = await response.json()

        # Check that at least one container is available
        assert isinstance(containers, list)
        assert len(containers) > 0
        print(f"Containers available: {len(containers)}")

        # Check that the hello-world container is available
        helloworld_containers = [c for c in containers if c["id"] == "hello-world"]
        assert len(helloworld_containers) == 1
        assert helloworld_containers[0]["count"] > 0
        print(
            f"'Hello World' containers reachable: {helloworld_containers[0]['count']}"
        )

        # Pick random offset
        offset = random.randint(0, 10)

        # Get IPs of nodes that can fulfill the `hello-world` job request
        ips_url = f"{ROUTER_URL}/api/v1/ips?container=hello-world&offset={offset}"
        async with session.get(ips_url) as response:
            assert response.status == 200
            ips = await response.json()

        # Check that at least one IP is available
        assert isinstance(ips, list)
        assert len(ips) > 0
        ip = ips[0]
        print(f"Selected IP: {ip}")

        # Create a job request with the selected node
        jobs_url = f"http://{ip}/api/jobs"
        dummy_data = {
            "some": "data",
            "for": "hello-world",
        }
        async with session.post(
            jobs_url, json={"containers": ["hello-world"], "data": dummy_data}
        ) as response:
            assert response.status == 200
            data = await response.json()
            job_id = data["id"]
            print(f"Job ID: {job_id}")

        # Wait for job to complete - 1 second should be more than enough
        await asyncio.sleep(1)

        # Fetch job result
        job_url = f"http://{ip}/api/jobs?id={job_id}"
        async with session.get(job_url) as response:
            assert response.status == 200
            data = await response.json()
            assert isinstance(data, list)
            assert len(data) == 1
            assert data[0]["id"] == job_id
            assert data[0]["status"] == "success"
            assert data[0]["result"]["container"] == "hello-world"
            assert (
                data[0]["result"]["output"]["output"]
                == "hello, world!, your input was: "
                f"{{'source': 1, 'data': {dummy_data}}}"
            )

        print("Integration test passed!")

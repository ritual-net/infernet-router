from __future__ import annotations

from asyncio import create_task, gather, sleep
from dataclasses import dataclass
from os import environ
from typing import Any

from aiohttp import ClientSession
from dotenv import load_dotenv

from logger import log
from sql import fetch_live_nodes

load_dotenv()

Hostname = str  # hostname or IP address and port


@dataclass
class NodeInfo:
    available: bool
    containers: list[dict[str, Any]]
    container_ids: list[str]
    pending: dict[str, int]


class NodeMonitor:
    """Monitors nodes' availability and pending job counts

    Private attributes:
        _base_nodes (dict[Hostname, NodeInfo]): Node objects for nodes included in
            ips.txt (explicitly specified nodes)
        _api_url (Optional[str]): URL of the explorer API to fetch live nodes from
        _available_nodes (dict[Hostname, NodeInfo]): Node objects for available nodes
        _shutdown (bool): Shutdown flag

    Methods:
        get_nodes: Select the next node hostnames / IPs to send a job to
        run_forever: Main lifecycle loop
        stop: Stop node monitor
    """

    def __init__(self, nodes: list[Hostname]) -> None:
        """Initializes NodeMonitor

        Args:
            nodes (list[Hostname]): List of node hostnames or IPs
        """
        super().__init__()

        # Nodes specified in ips.txt
        self._base_nodes: dict[Hostname, NodeInfo] = {
            node: NodeInfo(available=False, containers=[], container_ids=[], pending={})
            for node in nodes
        }

        # URL of the explorer API to fetch live nodes
        self._api_url = environ.get("API_URL")

        # Available nodes, including explicitly specified and live nodes
        self._available_nodes: dict[Hostname, NodeInfo] = {}

        # Shutdown flag
        self._shutdown = False

    async def _update_node(
        self: NodeMonitor, host: Hostname, nodes: dict[Hostname, NodeInfo]
    ) -> None:
        """Fetches latest information for given node, updating its NodeInfo
        object in place. If node does not respond, marks it as unavailable.

        Args:
            host (Hostname): Node hostname or IP
            nodes (dict[Hostname, NodeInfo]): Node info
        """
        try:
            async with ClientSession() as session:
                # Ping node for pending jobs
                async with session.get(f"http://{host}/info", timeout=3) as response:
                    if response.status == 200:
                        # Update node info
                        data = await response.json()
                        nodes[host] = NodeInfo(
                            available=True,
                            containers=data["containers"],
                            container_ids=[
                                container["id"] for container in data["containers"]
                            ],
                            pending=data["pending"],
                        )
                        return

        except Exception:
            pass

        # Node is not available
        if nodes[host].available:
            log.error("Node not available", node=host)
            nodes[host].available = False

    async def _get_live_nodes(self: NodeMonitor) -> dict[Hostname, NodeInfo]:
        """Fetches live nodes from the database

        If `self._api_url` is set, fetches live nodes from the explorer API.

        Returns:
            dict[Hostname, NodeInfo]: Node objects for live nodes
        """

        if self._api_url:
            return {
                # Hostname is ip:port for each node. Default port is 4000
                f'{node["ip"]}:{node["port"] if "port" in node else "4000"}': NodeInfo(
                    available=False, containers=[], container_ids=[], pending={}
                )
                for node in await fetch_live_nodes(self._api_url)
            }

        return {}

    async def run_forever(self: NodeMonitor) -> None:
        """Main lifecycle loop

        Continuously polls nodes for availability and updates `self._base_nodes` and
        `self._available_nodes`.

        `self._available_nodes` is a combination of all `self._base_nodes` (explicitl
        specified nodes that are online) and live nodes from the database.
        `get_live_nodes` is called every iteration to fetch the latest live nodes.

        The availability of each node is checked by pinging the node's `/info` endpoint.
        """
        while not self._shutdown:
            # Base nodes
            tasks = [
                create_task(self._update_node(host, self._base_nodes))
                for host in self._base_nodes
            ]

            # Live nodes
            live_nodes = await self._get_live_nodes()
            tasks += [
                create_task(self._update_node(host, live_nodes))
                for host in live_nodes
                if host not in self._base_nodes
            ]

            # Wait for all tasks to complete
            await gather(*tasks)

            # Combine base and live nodes
            all_nodes = {**self._base_nodes, **live_nodes}

            # Filter available nodes
            self._available_nodes = {
                host: node
                for host, node in all_nodes.items()
                if all_nodes[host].available
            }
            log.debug(
                "Available nodes",
                nodes=self._available_nodes.keys(),
                count=len(self._available_nodes),
            )

            await sleep(30)

    def get_nodes(
        self: NodeMonitor, containers: list[str], n: int = 3, offset: int = 0
    ) -> list[Hostname]:
        """Select the next node hostname / IP to send a job to

        Returns the next n nodes to send a job to, based on the pending job count.
        If no nodes running the requested containers are available, returns None.
        Optionally, an offset can be provided to skip the first `offset` nodes.

        Args:
            containers (list[str]): List of container IDs
            n (int): Maximum number of nodes to return
            offset (int): Offset to start from

        Returns:
            list[Hostname]: List of node hostnames or IPs
        """
        # Filter available nodes by running containers
        filtered_nodes = [
            host
            for host in self._available_nodes
            if all(
                container in self._available_nodes[host].container_ids
                for container in containers
            )
        ]

        # Sort nodes by the lowest pending job count
        sorted_nodes = sorted(
            filtered_nodes, key=lambda x: sum(self._available_nodes[x].pending.values())
        )

        # Top n nodes after  offset
        return sorted_nodes[offset : offset + n]

    def get_containers(self: NodeMonitor) -> list[dict[str, Any]]:
        """Returns containers running on all available nodes, with counts

        Returns:
            list[dict[str, Any]]: List of containers running on available nodes, with
                counts and descriptions
        """

        containers = {}
        for node in self._available_nodes.values():
            for container in node.containers:
                if container["id"] not in containers:
                    containers[container["id"]] = {"count": 1}
                else:
                    containers[container["id"]]["count"] += 1

                # First non-empty description is used
                if (
                    "description" not in containers[container["id"]]
                    and "description" in container
                ):
                    containers[container["id"]]["description"] = container[
                        "description"
                    ]

        return [
            {
                "id": id,
                "count": data["count"],
                **({"description": data["description"]} if data["description"] else {}),
            }
            for id, data in containers.items()
        ]

    async def stop(self: NodeMonitor) -> None:
        """Stop node monitor"""
        self._shutdown = True

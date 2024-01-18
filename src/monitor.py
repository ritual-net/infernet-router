from __future__ import annotations

from asyncio import create_task, gather, sleep
from dataclasses import dataclass
from typing import Any, Optional

from aiohttp import ClientSession

from logger import log

IPAddress = str


@dataclass
class NodeInfo:
    available: bool
    containers: list[dict[str, Any]]
    container_ids: list[str]
    pending: dict[str, int]


class NodeMonitor:
    """Monitors nodes' availability and pending job counts

    Private attributes:
        _nodes (dict[IPAddress, NodeInfo]): Node info
        _shutdown (bool): Shutdown flag

    Methods:
        run_forever: Main lifecycle loop
        get_next_node_ip: Returns IP of next node to send a job to, based on pending
            job count
    """

    def __init__(self, nodes: list[IPAddress]) -> None:
        """Initializes NodeMonitor

        Args:
            nodes (list[IPAddress]): List of node IPs
        """
        super().__init__()
        self._nodes: dict[IPAddress, NodeInfo] = {
            node: NodeInfo(available=False, containers=[], container_ids=[], pending={})
            for node in nodes
        }
        self._shutdown = False

    async def _update_node(self: NodeMonitor, node: IPAddress) -> None:
        """Updates pending jobs count for node in `_available_nodes`. If node does not
        respond, updates availability by removing node from `_available_nodes`.

        Args:
            node (IPAddress): Node IP
        """
        try:
            async with ClientSession() as session:
                # Ping node for pending jobs
                async with session.get(f"http://{node}/info", timeout=5) as response:
                    if response.status == 200:
                        # Update node info
                        data = await response.json()
                        self._nodes[node] = NodeInfo(
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
        if self._nodes[node].available:
            log.error("Node not available", node=node)
            self._nodes[node].available = False

    async def _update_all_nodes(self: NodeMonitor) -> None:
        """Updates availability for all nodes in `_nodes` asynchronously"""
        tasks = [create_task(self._update_node(node)) for node in self._nodes]
        await gather(*tasks)

    async def run_forever(self: NodeMonitor) -> None:
        """Main lifecycle loop

        Continuously polls nodes for availability and updates `_available_nodes` with
        pending job counts. Runs forever.
        """
        while not self._shutdown:
            await self._update_all_nodes()
            log.info(
                "Available nodes",
                nodes=[node for node in self._nodes if self._nodes[node].available],
            )

            await sleep(5)

    def get_next_node_ip(
        self: NodeMonitor, containers: list[str]
    ) -> Optional[IPAddress]:
        """Selects the next node to send a job to

        Returns the node with the lowest pending job count that has all containers
        required for the job. If no nodes have all containers, returns None.

        Args:
            containers (list[str]): List of container IDs

        Returns:
            IPAddress: IP address of node
        """
        try:
            return min(
                [
                    # Filter available nodes by running containers
                    node
                    for node in self._nodes
                    if self._nodes[node].available
                    and all(
                        container in self._nodes[node].container_ids
                        for container in containers
                    )
                ],
                # Select node with lowest pending job count
                key=lambda x: sum(self._nodes[x].pending.values()),
            )
        except ValueError:
            # No ready nodes
            return None

    async def stop(self: NodeMonitor) -> None:
        """Stop node monitor"""
        self._shutdown = True

import asyncio
import signal

from monitor import NodeMonitor
from os import environ
from rest import RESTServer
from logger import log


def read_ips(filepath: str = "ips.txt") -> list[str]:
    """Read node IPs from filepath

    Args:
        filepath (str, optional): Filepath to read from. Defaults to "ips.txt".

    Returns:
        list[str]: List of node IPs
    """
    with open(filepath, "r") as file:
        return file.read().splitlines()


async def shutdown(
    signal: signal.Signals, monitor: NodeMonitor, rest: RESTServer
) -> None:
    """Gracefully shutdown node.

    Args:
        signal (signal.Signals): Signal to handle
        rest (RESTServer): REST server
    """
    log.info(f"Received exit signal {signal.name}...")
    await monitor.stop()
    await rest.stop()
    log.info("Shutdown complete.")


async def main() -> None:
    """Entry point for router"""

    # Read node IPs from file
    nodes = read_ips()
    port = environ.get("PORT", "4000")

    monitor = NodeMonitor(nodes)
    server = RESTServer(port, monitor)

    # Register signal handlers for graceful shutdown
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(
            sig, lambda s=sig: asyncio.create_task(shutdown(s, monitor, server))
        )

    # Run tasks
    tasks = [
        asyncio.create_task(monitor.run_forever()),
        asyncio.create_task(server.run_forever()),
    ]

    # Wait for any task to complete
    done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    for task in done:
        # Check if any tasks failed
        if task.exception() is not None:
            # Log exception
            log.error("Task exception", exception=task.exception())


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())

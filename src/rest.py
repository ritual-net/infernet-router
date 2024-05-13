from __future__ import annotations

from asyncio import CancelledError, Event, create_task
from datetime import timedelta
from typing import Tuple

from hypercorn.asyncio import serve
from hypercorn.config import Config
from quart import Quart, Response, jsonify, request
from quart_rate_limiter import RateLimiter, rate_limit

from logger import log
from monitor import NodeMonitor


class RESTServer:
    """REST server for router"""

    def __init__(
        self: RESTServer,
        port: str,
        monitor: NodeMonitor,
    ) -> None:
        """Initializes RESTServer

        Args:
            port (str): Port to serve on
            monitor (NodeMonitor): Node monitor
        """
        self._address = "0.0.0.0"
        self._port = port
        self._monitor = monitor

        # Webserver setup
        self._app = Quart(__name__)
        self._app_config = Config.from_mapping(
            {"bind": [f"{self._address}:{self._port}"]}
        )

        # Initialize rate limiter
        RateLimiter(self._app)

        # Register Quart routes
        self.register_routes()

        # Event to signal shutdown
        self._shutdown_event = Event()

        log.info("Initialized RESTServer", port=self._port)

    def register_routes(self: RESTServer) -> None:
        """Registers Quart webserver routes"""

        @self._app.route("/api/v1/ips", methods=["GET"])
        @rate_limit(10, timedelta(seconds=30))
        async def ips() -> Tuple[Response, int]:
            """Returns IPs of nodes that can fulfill a job request"""

            containers = request.args.getlist("container")
            if not containers:
                return (
                    jsonify({"error": "No containers specified"}),
                    400,
                )

            # Optional query parameters n and offset
            n = request.args.get("n", default=3, type=int)
            offset = request.args.get("offset", default=0, type=int)

            return (
                jsonify(self._monitor.get_nodes(containers, n, offset)),
                200,
            )

        @self._app.route("/api/v1/containers", methods=["GET"])
        @rate_limit(5, timedelta(seconds=30))
        async def containers() -> Tuple[Response, int]:
            """Returns containers running across the network"""

            return (
                jsonify(self._monitor.get_containers()),
                200,
            )

    async def run_forever(self: RESTServer) -> None:
        """Main RESTServer lifecycle loop. Uses production hypercorn server"""

        log.info("Serving REST webserver", addr=self._address, port=self._port)

        async def shutdown_trigger() -> None:
            """Shutdown trigger for hypercorn"""
            await self._shutdown_event.wait()

        server_task = create_task(
            serve(
                app=self._app,
                config=self._app_config,
                mode="asgi",
                # Stop server when stop event is set
                shutdown_trigger=shutdown_trigger,
            )
        )

        try:
            await server_task
        except CancelledError:
            pass  # Expected due to cancellation

    async def stop(self: RESTServer) -> None:
        """Stops the RESTServer."""
        log.info("Stopping REST webserver")

        # Set shutdown event to stop server
        self._shutdown_event.set()

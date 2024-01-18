from __future__ import annotations

from asyncio import CancelledError, Event, create_task
from typing import Tuple

from hypercorn.asyncio import serve
from hypercorn.config import Config
from quart import Quart, jsonify, request, Response

from monitor import NodeMonitor
from logger import log


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

        # Register Quart routes
        self.register_routes()

        # Event to signal shutdown
        self._shutdown_event = Event()

        log.info("Initialized RESTServer", port=self._port)

    def register_routes(self: RESTServer) -> None:
        """Registers Quart webserver routes"""

        @self._app.route("/api/v1/ip", methods=["GET"])
        async def ip() -> Tuple[Response, int]:
            """Returns the next node IP to send a job to"""

            containers = request.args.getlist("container")
            if not containers:
                return (
                    jsonify({"error": "No containers specified"}),
                    400,
                )

            next_node_ip = self._monitor.get_next_node_ip(containers)

            if next_node_ip is None:
                return (
                    jsonify({"error": "No nodes available"}),
                    503,
                )
            else:
                return (
                    jsonify({"ip": next_node_ip}),
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

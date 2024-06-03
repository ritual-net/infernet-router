from typing import Any, cast

from aiohttp import ClientSession

from logger import log


async def fetch_live_nodes(api_url: str) -> list[dict[str, Any]]:
    """Fetches live nodes using the explorer REST API.

    Args:
        api_url (str): URL of the explorer API

    Returns:
        list[dict[str, Any]]: List of live nodes
    """
    url = f"{api_url}/api/nodes?minutes_past=60"
    try:
        async with ClientSession() as session:
            async with session.get(url) as response:
                # Check if the HTTP request was successful
                if response.status == 200:
                    body = await response.json()
                    return cast(list[dict[str, Any]], body["data"])
                else:
                    log.error("Failed to fetch live nodes", status=response.status)
    except Exception as e:
        log.error(f"Failed to fetch live nodes: {str(e)}")

    return []

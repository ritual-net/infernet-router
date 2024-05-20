from os import environ

# Interval to poll nodes for availability
REFRESH_INTERVAL = float(environ.get("REFRESH_INTERVAL", 30))

# Rate limit for REST API in requests per minute
RATELIMIT_REQS_PER_MIN = int(environ.get("RATELIMIT_REQS_PER_MIN", 10))

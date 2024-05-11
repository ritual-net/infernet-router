# Infernet Router

A lightweight REST server to help route requests to Infernet nodes at scale. This service **does not** route requests directly. Instead, it returns an Infernet node IP to send requests to. As such, it can be used in a 2-step process, where the client:
1. Requests an IP from the Infernet Router.
2. Sends Infernet API request(s) directly to that IP.

**Currently, the Infernet Router:**
- Maintains list of available (healthy) Infernet nodes, based on either / both:
  1. A list of pre-specified addresses.
  2. A list of live nodes in the network discovered via the centralized metric sender.
- Continuously fetches:
  - running containers, and "routes" to nodes that support containers requester by the client.
  - number of pending jobs, and "routes" to least busy node.

**In the future, it could also:**
- Consider node resource utilization, instead of just pending job count.
- Assign weights to different job types.

## Setup

There are two ways the router can discover IPs of nodes to route to:
  1. A list of pre-specified hostnames / IP addresses.
  2. A list of live nodes discovered via API requests to the [Node Explorer](https://github.com/ritual-net/infernet-node-explorer) backend, which interfaces with the centralized metric sender.

### Pre-specified hosts

Manually specifying hostnames / IPs for the router to check is useful because:

1. You can control the subset of nodes you route to.
2. You can specify private, undiscoverable, or firewalled IPs that the router has priviledged access to.
3. You might not need, want, or be able to connect to a Node Explorer backend for live node discovery.

**To enable:** All that's required is an `ips.txt` file, which is a newline-separated list of Infernet node addresses. Those could be in the form of `ip_address:port`, or a human-readable hostname. See [example file](./ips.txt.example).

```bash
# Copy example file
cp ips.txt.example ips.txt

# Fill in IP addresses / hosts, one on each line #
```

### Live nodes via Node Explorer

Pulling live node information is useful because:
1. The router maintains a dynamic list of node IPs, i.e. discover new nodes and drop old ones.
2. You don't need to pre-specify any node addresses and maintain the `ips.txt` file.

**Note** that only nodes with [forward_stats](https://docs.ritual.net/infernet/node/configuration#forward_stats-boolean) enabled can be discovered via this method.

**To enable:** Specify `API_URL` that points to a Node Explorer REST API, as an environment variable, e.g.:

```bash
export API_URL=...
```

## Deployment

### Locally via Docker

```bash
# Optional: specify port (defaults to 4000)
PORT=4000

# Run it
docker compose up -d
```

### Locally via source

```bash
# Create and source new python venv
python3.11 -m venv env
source ./env/bin/activate

# Install dependencies
make install

# Optional: specify port (defaults to 4000)
PORT=4000

# Run node
make run
```

### AWS / GCP

This Infernet Router is deployed as part of the [infernet-deploy](https://github.com/ritual-net/infernet-deploy) repo.


## Publishing a Docker image

```bash
# Set tag
tag="0.1.0"

# Force linux build (useful when building on Mac)
docker build --platform linux/amd64 -t ritualnetwork/infernet-router:$tag .

# Push to Dockerhub
docker push ritualnetwork/infernet-router:$tag
```


## API

Currently, the router only supports a single endpoint:

#### GET `/api/v1/ip`

Returns an Infernet node IP to send requests to.

- **Method:** `GET`
- **URL:** `/api/v1/ip`
- **Query Parameters:**
  - `container` (`string`, repeatable): IDs of containers required for the job. Multiple can be specified by repeating this parameter (e.g., `?container=inference1&container=inference2`). Only IPs of nodes running the specified containers will be selected.
- **Response:**
  - **Success:**
    - **Code:** `200 OK`
    - **Content:**
    `{ "ip": string }`
      - `ip`: IP address of an Infernet node
  - **Failure:**
    - **Code:** `503 Service Unavailable`
    - **Content:**
        `{"error": string}`
      - `error`: Error message

## License

[BSD 3-clause Clear](./LICENSE)

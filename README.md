# Infernet Router

A lightweight REST server to help route requests to Infernet nodes at scale. This service **does not** route requests directly. Instead, it returns a list of Infernet node IPs that can fulfill requests. As such, it can be used in a 2-step process, where the client:
1. Requests a list of IPs from the Infernet Router.
2. Sends Infernet API request(s) directly to one or more nodes.

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

## Live deployment

The official deployment of the Infernet Router **is live** at **`infernet-router.ritual.net`**.

You can query it as follows:

```bash
curl infernet-router.ritual.net/api/v1/ips?container=hello-world
```

## Setup

There are two ways the router can discover IPs of nodes to route to:
  1. A list of pre-specified hostnames / IP addresses.
  2. A list of live nodes discovered via API requests to the [Node Explorer](https://github.com/ritual-net/infernet-node-explorer) backend, which interfaces with the centralized metric sender.

### 0. Modify configurations (optional)

Export the following environment variables to modify default configurations. See [.env.example](.env.example) for examples.

- `PORT` (`int`): The router server's port. Defaults to `4000`.
- `REFRESH_INTERVAL` (`float`): Node polling interval in seconds. Defaults to `30`.
- `RATELIMIT_REQS_PER_MIN` (`int`): Rate limit for requests per minute. Defaults to `10`.
- `API_URL` (`str`): Node Explorer REST API. See [2](#2-live-nodes-via-node-explorer). Optional (empty by default).

### 1. Pre-specified hosts

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

### 2. Live nodes via Node Explorer

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

Currently, the router only supports two endpoints:

#### 1. GET `/api/v1/ips`

Returns Infernet node IPs to send requests to.

- **Method:** `GET`
- **URL:** `/api/v1/ips`
- **Query Parameters:**
  - `container` (`string`, _repeatable_): IDs of containers required for the job. Multiple can be specified by repeating this parameter (e.g., `?container=inference1&container=inference2`). Only IPs of nodes running the specified containers will be returned.
  - `n` (`integer`, _optional_): Number of IPs to return. Defaults to `3`.
  - `offset` (`integer`, _optional_): Number of node IPs to skip before returning.
- **Response:**
  - **Success:**
    - **Code:** `200 OK`
    - **Content:** `string[]`
      - An array of node IPs
  - **Failure:**
    - **Code:** `400`
    - **Content:**
        `{"error": "No containers specified"}`
        - If no containers are specified


#### 2. GET `/api/v1/containers`

Returns all discoverable services (containers) running on the Infernet Network.

- **Method:** `GET`
- **URL:** `/api/v1/containers`
- **Response:**
  - **Success:**
    - **Code:** `200 OK`
    - **Content:** Array of container objects
    `{ "id": string, "count": number[, "description": string] }[]`
      - `id`: Container (service) ID
      - `count`: Number of discoverable nodes running this service
      - `description` (`optional`): Description of the container

## License

[BSD 3-clause Clear](./LICENSE)

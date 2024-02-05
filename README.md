# Infernet Router

A lightweight REST server to help route requests to Infernet nodes at scale. This service **does not** route requests directly. Instead, it returns an Infernet node IP to send requests to. As such, it can be used in a 2-step process, where the client:
1. Requests an IP from the Infernet Router.
2. Sends Infernet API request(s) directly to that IP.

<u>Currently, the Infernet Router:</u>
- Maintains list of available (healthy) Infernet nodes, based on a list of pre-specified IP addresses.
- Continuously fetches:
  - running containers, and "routes" to nodes that support containers requester by the client.
  - number of pending jobs, and "routes" to least busy node.

<u>In the future, it could also:</u>
- Consider node resource utilization, instead of just pending job count.
- Assign weights to different job types.

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


## Deployment

### Locally

#### Setup

All that's required is an `ips.txt` file, which is a newline-separated list of Infernet node hostnames. Those could be in the form of `ip_address:port`, or `https://hostname`. See [example file](./ips.txt.example).

```bash
# Copy example file
cp ips.txt.example ips.txt

# Fill in IP addresses / hosts, one on each line #
```

## Deploying the router

### Locally via Docker

```bash
# Set tag
tag="0.1.0"

# Build it
docker build -t ritualnetwork/infernet-router:$tag .

# Specify port
PORT=4000

# Run it
docker run -p $PORT:$PORT -e PORT=$PORT -v ./ips.txt:/app/ips.txt ritualnetwork/infernet-router:$tag
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

## License

[BSD 3-clause Clear](./LICENSE)

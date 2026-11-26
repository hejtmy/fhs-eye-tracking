# Running Gaze Lab on a server

Gaze Lab is one container: a Python process that serves the web app and the
API on port 8000. It needs no database. Uploaded recordings are files in one
folder (a Docker volume).

## 1. On your own computer or a lab machine

You need Docker with the Compose plugin (Docker Desktop, OrbStack, or Docker
Engine on Linux).

```sh
git clone <this repository> gaze-lab && cd gaze-lab
docker compose up -d --build
```

Open <http://localhost:8000>. The first build downloads the base images and
the Python packages and takes a few minutes; later starts take seconds. The
image is about 1 GB.

| Task | Command |
| --- | --- |
| See whether it is healthy | `docker compose ps` |
| Read the log | `docker compose logs -f` |
| Stop (uploads are kept) | `docker compose down` |
| Stop and delete all uploads | `docker compose down -v` |
| Update to a new version | `git pull && docker compose up -d --build` |

## 2. In a classroom network

By default the app only answers on the machine it runs on. To let other
computers on the same network reach it, create a file `.env` next to
`compose.yaml` (copy `.env.example`) and set:

```sh
GAZELAB_BIND=0.0.0.0
GAZELAB_PORT=8000
GAZELAB_WORKERS=2
```

Run `docker compose up -d` again. Students open `http://<name or IP of the
machine>:8000`. On Linux, allow the port in the firewall (for example
`sudo ufw allow 8000/tcp`).

In this set-up there is no encryption and no password. That is acceptable for
the simulated examples in a trusted room, not for recordings of real people
on a shared network.

## 3. On the internet, with HTTPS and a password

You need a server with a public address and a domain name pointing to it
(ports 80 and 443 open). The second compose file adds [Caddy](https://caddyserver.com),
which obtains and renews the certificate by itself and asks for one shared
user name and password.

1. Create the password hash (it prints one line starting with `$2a$`):

   ```sh
   docker run --rm caddy:2 caddy hash-password --plaintext 'the password you chose'
   ```

2. Put this in `.env`. Keep the single quotes around the hash:

   ```sh
   GAZELAB_DOMAIN=gazelab.example.org
   GAZELAB_USER=class
   GAZELAB_PASSWORD_HASH='$2a$14$…the line from step 1…'
   GAZELAB_WORKERS=2
   ```

3. Start both services:

   ```sh
   docker compose -f compose.yaml -f compose.https.yaml up -d --build
   ```

Open `https://gazelab.example.org`. The app itself is no longer published on
port 8000; everything goes through the proxy. Use the same two `-f` options
for `ps`, `logs`, `down` and updates.

If your university already runs a reverse proxy with single sign-on, skip
`compose.https.yaml` and point that proxy at port 8000 of this machine. Two
things to configure there: allow request bodies as large as
`GAZELAB_MAX_UPLOAD_MB`, and do not buffer or time out requests under about
two minutes (large files take a while to read).

## Settings

All settings are environment variables, read from `.env` by Compose.

| Variable | Default | Meaning |
| --- | --- | --- |
| `GAZELAB_BIND` | `127.0.0.1` | Address the app is published on. `0.0.0.0` for the whole network. |
| `GAZELAB_PORT` | `8000` | Port on the host. |
| `GAZELAB_WORKERS` | `1` | Worker processes. Use 2–4 when a class works at the same time. Each worker keeps its own cache, so memory grows with this number. |
| `GAZELAB_MAX_UPLOAD_MB` | `300` | Largest upload, all files of one dataset together. |
| `GAZELAB_MAX_ROWS` | `3000000` | Most samples one dataset may contain. |
| `GAZELAB_UPLOAD_TTL_HOURS` | `168` | Uploads are deleted this many hours after they were last used. `0` keeps them until you delete them. |
| `GAZELAB_CACHE_STEPS` | `64` | Step results kept in memory per worker. |
| `GAZELAB_POLARS_COMPAT` | `0` | `1` builds the image for older CPUs without AVX2. Somewhat slower; needs `--build`. |
| `GAZELAB_DOMAIN`, `GAZELAB_USER`, `GAZELAB_PASSWORD_HASH` | none | Only for `compose.https.yaml`. |

Outside Docker the same variables work, plus `GAZELAB_DATA_DIR` (where
uploads are stored, default `./var`) and `GAZELAB_PLUGINS` (folder with
plug-in steps).

## How much machine

Measured on a laptop: a recording of 1.1 million samples (10 participants,
about 3 hours at 100 Hz) loads and runs through cleaning, both fixation
detectors and saccade detection in about 10 seconds, of which I-DT takes 4;
a figure takes 0.1–0.3 seconds. The container uses about 260 MB of memory
after running the examples. A million samples held in the cache at several
steps costs a few hundred MB.

For a class of 30 working on the examples, 2 CPU cores and 2 GB of memory are
plenty. For large real recordings, plan 4 GB and keep `GAZELAB_WORKERS` at 2.

## Where the data are, and who can see them

- Uploads are stored in the volume `gazelab-data` (inside the container:
  `/data/datasets/<id>/`). Nothing is sent anywhere else.
- Each upload gets a long random id. The id is stored in the pipeline of the
  person who uploaded it (in their browser, and in any pipeline file they
  save). Whoever has the id can read the upload; there are no user accounts.
  With the password set-up of section 3, only people who know the password
  can reach the server at all.
- Uploads are removed automatically after `GAZELAB_UPLOAD_TTL_HOURS` without
  use. People can delete their own upload at once in the Load step
  (“Delete upload”).
- Pipelines are saved in the browser, not on the server. “Save” downloads a
  pipeline file; “Export results” downloads the results and a reproducible copy.
- The rest of the container's file system is read-only and the process runs
  as an unprivileged user.

To back up or inspect uploads:

```sh
docker run --rm -v gaze-lab_gazelab-data:/data -v "$PWD":/backup alpine tar czf /backup/gazelab-uploads.tgz -C /data .
```

(The volume name starts with the folder name of the repository; check with
`docker volume ls`.)

## Adding your own steps on a running server

Put a `.py` file into `plugins/` on the host and restart:

```sh
docker compose restart gazelab
```

The folder is mounted read-only into the container. A working example is in
`plugins/_example_velocity_filter.py`; the contract is in
[extending.md](extending.md). Plug-ins run with the same rights as the app, so
only install code you trust.

## When something does not work

| Symptom | Likely cause |
| --- | --- |
| The page says it cannot reach its server | The container is not running or still starting: `docker compose ps`, `docker compose logs`. |
| Uploading fails immediately with “limited to … MB” | Raise `GAZELAB_MAX_UPLOAD_MB` (and the proxy's body limit, which `compose.https.yaml` takes from the same variable). |
| “This dataset is no longer on the server” | The upload expired or the volume was deleted. Upload again; the pipeline is still in the browser. |
| A step that came from a plug-in is “unknown” | The plug-in file is missing on this server or failed to load; see the log at start-up. |
| Certificates are not issued | The domain does not point to this server, or ports 80/443 are blocked. `docker compose -f compose.yaml -f compose.https.yaml logs proxy` says which. |
| Container is “unhealthy”, the log says “Missing required CPU features” and “Child process … died” | The CPU (or the VM's CPU type) lacks AVX2. In Proxmox set the VM's processor type to `host` and stop/start the VM. If the hardware itself is too old, set `GAZELAB_POLARS_COMPAT=1` in `.env` and run `docker compose up -d --build`. |
| `port is already allocated` | Something else uses the port. Set another `GAZELAB_PORT` in `.env`. |

# Limits

A terminal app that displays OS configuration and limits helpful to debug issues.

## Usage

There are options how you can run this app:

### Docker

This runs inside a container, which is helpful if you want to inspect containers

- Build
```shell
docker build -f Dockerfile -t limits:latest .
```

- Run
```shell
docker run -it limits:latest
```

### Directly run as a script:

If you want to inspect from a local machine or VM, you can run this as script. No need to install any dependencies except `uv`

```shell
uv run limits.py
```

### Build and run

This is the approach you take if you want to extend the app.
Install and update the dependencies first and then run the app in debug mode like a Pythonista!

- Install dependencies and run

```shell
uv sync
```

```shell
uv run limits.py
```

# Key bindings

Press `q` to quit
Press `r` to refresh

# Dependencies

Optional

- textual-dev is added to debug
- ruff for formatting

This allows you to run in debug mode

```shell
textual run limits.py
```

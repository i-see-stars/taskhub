# TaskHub

## Build the Docker image

From the project root (where `Dockerfile` is):

```bash
docker build -t taskhub .
```

## Run the container

```bash
docker run --rm -p 8000:80 taskhub
```

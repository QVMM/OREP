# OREP Local Development Scripts

## Start Backend

```bash
./scripts/dev/start-backend-local.sh
```

The backend launcher now checks and starts the local MinIO instance first, using:

```text
minio-data
```

To start storage independently:

```bash
./scripts/dev/start-minio-local.sh
```

The script reads:

```text
backend/.env.local
```

That file is for local development only. It is ignored by git and Docker build contexts, so it will not be included in the production release package.

Production deployment still uses:

```text
/opt/orep/.env.production
```

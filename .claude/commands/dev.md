---
allowed-tools: Bash
argument-hint: [up|down|status|logs|rebuild|reset-data]
---

Manage the SelfPace Docker Compose stack. The argument is: **$ARGUMENTS**

Run the appropriate block below based on the argument. After any action that starts or stops services, run the health check at the end.

---

## up — Build and start all services

```bash
docker compose up --build -d
```

## down — Stop all services

```bash
docker compose down
```

## status — Show service state and recent logs

```bash
docker compose ps
echo "--- backend tail ---"
docker compose logs --tail=20 backend
echo "--- frontend tail ---"
docker compose logs --tail=20 frontend
```

## logs — Follow live logs (both services)

```bash
docker compose logs -f
```

## rebuild — Full no-cache rebuild, then start

```bash
docker compose down
docker compose build --no-cache
docker compose up -d
```

## reset-data — Destructive: wipe /data volume

**STOP. Before running any commands, confirm with the user:**

> "This will delete all Parquet files, raw activity files, and imports in the /data volume. This cannot be undone. Type YES to confirm."

Only proceed if the user explicitly responds with "YES". Then:

```bash
docker compose down
docker volume rm selfpace_data 2>/dev/null || true
docker compose up --build -d
```

---

## Health check (run after up / rebuild / reset-data)

```bash
sleep 3
curl -sf http://localhost:8000/health && echo "backend OK" || echo "backend not responding"
curl -sf http://localhost:3000 -o /dev/null && echo "frontend OK" || echo "frontend not responding"
```

Report the health check results to the user.

# Fuel Project

Django + PostGIS service to compute an optimized set of fuel stops along a driving route using OpenRouteService (ORS). The project:
- Uses ORS for geocoding and routing.
- Stores fuel station data in PostGIS (`FuelStation` model).
- Caches expensive external API calls and final results in Redis to reduce ORS requests.

---

## Installatioin (Non-Docker)
The project uses `pyproject.toml`.

- Install uv in your system if its not already installed.
```
uv venv
suurce .venv/bin/activate
```

- Install dependencies:
```
uv sync
```

- Set up other dependencies like postgis, and redis from respective pakages's homepage.

---

## Local (non-Docker) setup
1. Copy `.env.example -> .env` and edit values.
2. Ensure PostGIS and Redis are running locally (or point `.env` to hosted services).
   - PostGIS: make sure DB is created and connection credentials match `.env`.
   - Redis: start the redis server (default on 127.0.0.1:6379).
3. Apply migrations:
```
python manage.py migrate
```
4. (Optional) Load or create `FuelStation` data in the DB.
5. Run development server:
```
python manage.py runserver
```

---

## Installation (Docker)

1. Set up the following env variables
```
  ORS_API_KEY=your_ors_api_key_here
  DJANGO_SECRET_KEY=replace_with_strong_secret_key
  DJANGO_DEBUG=True
  DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

  POSTGRES_DB=fueldb
  POSTGRES_USER=postgres
  POSTGRES_PASSWORD=postgres
  POSTGRES_HOST=localhost
  POSTGRES_PORT=5432
```

2. Build and run
```
cd fuel_project
docker compose up --build
```
3. Inside the `web` container run migrations:
```
docker compose exec web python manage.py migrate
```
4. The API should be available on `http://localhost:8000/api`.

---

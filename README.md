# 832401126_calculator_backend

Back end of the **Front-End / Back-End Separation Calculator System** assignment.

This service owns every piece of computation: it validates the input,
parses the mathematical expression, evaluates it, stores every successful
calculation in a SQLite database and serves the calculation history over a
clean HTTP API. The front end (`832401126_calculator_frontend`) only sends
expressions and displays whatever this service returns — it never computes
anything itself.

> ⚠️ **No `eval` / `exec` anywhere.** User expressions are processed by a
> hand-written lexer → recursive-descent parser → AST evaluator pipeline.
> Arbitrary code execution is impossible by construction.

---

## Technology stack

| Layer       | Choice                                            |
|-------------|---------------------------------------------------|
| Language    | Python 3.10+                                      |
| Web framework | Flask 3.x                                        |
| Database    | SQLite 3 (single file, zero configuration)        |
| CORS        | flask-cors                                        |
| WSGI server | gunicorn (production) / Flask dev server (local)  |
| Tests       | Python `unittest` (no extra dependencies)         |

## Project structure

```
832401126_calculator_backend/
├── app.py                     # Flask application factory + entry point
├── requirements.txt
├── README.md
├── codestyle.md
├── .gitignore
├── src/
│   ├── config.py              # configuration (env-var driven)
│   ├── controller/
│   │   └── calculator_controller.py   # HTTP API endpoints
│   ├── service/
│   │   ├── calculator_service.py      # evaluate + persist flow
│   │   └── history_service.py         # history CRUD
│   ├── model/
│   │   ├── database.py                # SQLite connection & schema
│   │   └── history_model.py           # record model
│   └── calculator/
│       ├── calculator.py      # public facade: safe_calculate()
│       ├── lexer.py           # tokenizer (whitelist of characters)
│       ├── parser.py          # recursive-descent parser -> AST
│       ├── evaluator.py       # AST evaluator + math rules
│       └── exceptions.py      # typed error hierarchy
└── tests/
    └── test_calculator.py     # 45 unit + API tests
```

## API design

All endpoints are under `/api` and return JSON. Successful and failed
responses share a consistent envelope:

```jsonc
// success
{ "success": true, "id": 1, "expression": "(1+2)*3", "result": "9", "created_at": "2026-10-07 20:30:00" }

// failure (HTTP 400/404)
{ "success": false, "message": "Division by zero" }
```

| Method | Endpoint              | Purpose                                        | Status codes        |
|--------|-----------------------|------------------------------------------------|---------------------|
| POST   | `/api/calculate`      | Evaluate `{"expression": "..."}` and store it  | 200, 400            |
| GET    | `/api/history`        | List history (`?q=`, `?limit=`, `?offset=`)    | 200, 400            |
| DELETE | `/api/history/{id}`   | Delete one history record                      | 200, 404            |
| DELETE | `/api/history`        | Delete **all** history (extension)             | 200                 |
| GET    | `/api/health`         | Liveness probe for deployment                  | 200                 |

Example:

```bash
curl -X POST http://localhost:5000/api/calculate \
  -H "Content-Type: application/json" \
  -d '{"expression": "(1+2)*3"}'
# => {"success":true,"id":1,"expression":"(1+2)*3","result":"9","created_at":"2026-10-07 20:30:00"}
```

## Runtime environment

- Python 3.10 or newer (developed and tested on 3.12)
- No external database server required — SQLite is embedded

## Installation

```bash
git clone https://github.com/<your-github>/832401126_calculator_backend.git
cd 832401126_calculator_backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Database initialization

The database is created automatically on first startup (no manual step):

- File: `instance/calculator.db` (created in `instance/`)
- Table: `calculation_history(id INTEGER PRIMARY KEY AUTOINCREMENT,
  expression TEXT, result TEXT, created_at TEXT)`
- To use a different path: `export DATABASE_PATH=/path/to/calculator.db`

To inspect the data:

```bash
sqlite3 instance/calculator.db "SELECT * FROM calculation_history ORDER BY id DESC LIMIT 5;"
```

## Startup

Local development (debug off by default):

```bash
python app.py        # listens on 0.0.0.0:5000
```

Production-style:

```bash
gunicorn -w 2 -b 0.0.0.0:5000 app:app
```

## Configuration (environment variables)

| Variable       | Default                | Purpose                                  |
|----------------|------------------------|------------------------------------------|
| `PORT`         | `5000`                 | HTTP port (Render injects this)          |
| `DATABASE_PATH`| `instance/calculator.db` | SQLite file location                   |
| `CORS_ORIGINS` | `*`                    | Comma-separated origins allowed to call the API |

## Connecting the front end

1. Start this back end (see above).
2. Point the front end at it. In
   `832401126_calculator_frontend/js/config.js`:

   ```js
   export const CONFIG = {
     apiBaseUrl: "http://localhost:5000",   // change to your backend URL
   };
   ```

3. The front end can be served statically (e.g. `python -m http.server 5500`)
   and will call `/api/*` on the back end via CORS.

## Tests

```bash
python -m unittest discover -s tests -v
# Ran 45 tests — OK
```

The suite covers: basic arithmetic, operator precedence, parentheses,
unary plus/minus, decimals, scientific functions, division by zero,
invalid expressions, code-injection attempts (`__import__("os")...`),
overflow, and every API endpoint end to end.

## Deployment (hosted, e.g. Render)

A `render.yaml` and `Dockerfile` are included:

- **Render**: push this repository to GitHub → *New Web Service* → Render
  auto-detects `render.yaml`. The service listens on `$PORT` and writes the
  database to a mounted disk (`/data`), so history survives restarts.
- **Docker**: `docker build -t calc-backend . && docker run -p 5000:5000 calc-backend`

See the assignment blog for the full deployment walkthrough.

## License & course info

Course assignment project by student **832401126**. See
[codestyle.md](codestyle.md) for the code standard this repository follows.

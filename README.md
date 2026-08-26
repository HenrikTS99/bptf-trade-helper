# Backpack.tf Trade Helper

BPTF Trade Helper is a FastAPI web application designed to help users manage their sell- and buyorders on the Team Fortress 2 trading site [backpack.tf](https://backpack.tf).

## Features

### Automated Price Scanning

Scheduled scanner updates buyorder and sellorder data hourly and every two hours for sellorders.
It will then update listing data, and detect outbids, undercuts, and competitor changes.

### Dashboard

- View all buyorders and sellorders with current status, if winning or beaten, and by how much.
- One-click actions to match or beat competitors by different amounts.

### History

Track listing state changes for buyorders and sellorders over time with filters for outbids, undercuts, price changes and competitor changes.
You can filter through which changes you would like to be displayed, with relevant filters on by default.

## Tech Stack

- FastAPI
- SQLAlchemy + SQLite
- Jinja2
- APScheduler
- Docker + Docker Compose
- HTMX
- PICO CSS

## Project Structure

```
├── app/
│   ├── core/           # Scanner, sync tracker, and backpack.tf API client
│   ├── db/             # Database setup and SQLAlchemy models
│   ├── models/         # Pydantic models and enums
│   ├── routers/        # API routes and views
│   ├── services/       # Business logic
│   ├── static/         # CSS
│   ├── templates/      # Jinja2 templates
│   ├── config.py       # Environment variables settings via pydantic-settings
│   ├── crud.py         # Database CRUD operations
│   ├── dependencies.py # Shared application instances (environment variables, API client and scanner)
│   ├── main.py         # Application entry point
│   └── scheduler.py    # Background task scheduler
├── tests/
├── Dockerfile
├── docker-compose.yml
└── pyproject.toml
```

## How to Run

### Prerequisites

Before you begin, make sure you have Docker and Docker Compose installed.

### Installation with Docker

1. Clone the repository:

```bash
git clone https://github.com/HenrikTS99/bptf-trade-helper.git
cd bptf-trade-helper
```

2. Create the `.env` file with the necessary environment variables

```bash
BP_API_KEY=your_api_key
BP_TOKEN=your_token
STEAM_ID=your_steam_id
```

You can get your backpack.tf token and api key here: https://next.backpack.tf/account/api-access

3. Build and run the Docker image: `docker compose up -d`
4. Access the application in your web browser at localhost:8001 or 127.0.0.1:8001

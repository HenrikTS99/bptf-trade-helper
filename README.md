# Backpack.tf Trade Helper

Bptf-trade-helper is a FastAPI web application designed to help users manage their sell- and buyorders on the Team Fortress 2 trading site [backpack.tf](https://backpack.tf).

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

4. Build and run the Docker image: docker compose up -d
5. Access the application in your web browser at localhost:8001 or 127.0.0.1:8001

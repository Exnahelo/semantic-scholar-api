# Semantic Scholar API Wrapper

A FastAPI-based wrapper for the Semantic Scholar API, providing endpoints for paper search, details, recommendations, reading list generation, and foundational paper discovery.

## Features

- Paper search with advanced filtering
- Detailed paper information retrieval
- Related paper recommendations
- Reading list generation
- Foundational paper discovery
- Caching for improved performance
- Semantic Scholar API key support

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/Exnahelo/semantic-scholar-api.git
   cd semantic-scholar-api
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. (Optional) Set your Semantic Scholar API key:
   ```bash
   export SEMANTIC_SCHOLAR_API_KEY=your_api_key_here
   ```

## Usage

Run the server:
```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`

Visit `http://localhost:8000/docs` for interactive API documentation.

## API Endpoints

- `GET /search` - Search for papers
- `GET /paper/{paper_id}` - Get paper details
- `GET /paper/{paper_id}/recommendations` - Get related papers
- `POST /reading-list` - Generate a reading list
- `GET /foundational/{paper_id}` - Get foundational papers

## Requirements

- Python 3.8+
- FastAPI
- Uvicorn
- Requests
- Pydantic
- Cachetools

## License

MIT
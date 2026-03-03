# HW-project to create shortened links 

* Alembic for database migrations 
* SQLAlchemy to simplify work with SQL (sql schemas are provided in `src/schemas/schemas.py`)
* Redis caching 
<!-- * Additional foo to get top links (cached too) -->

The references of code are taken from 
https://github.com/AI-25-HSE-Team-18/toxic-messages-handling-project/tree/checkpoint4/kondratevaai/last_model/0/src

### API Endpoints

#### Link Management
- `POST /links/shorten` - Create shortened link
- `GET /{short_code}` - Redirect and track click
- `GET /links/{short_code}/stats` - Get link statistics
- `PUT /links/{short_code}` - Update link
- `DELETE /links/{short_code}` - Delete link
- `GET /links/search?original_url=...` - Search links
- `GET /links/analytics/top?limit=10` - Get most accessed links (cached)

#### User Management  
- `POST /users/register` - Register new user
- `POST /users/login` - Get authentication token

## Using 
NOTE: Temporarily deployed at Render [link]

### Start locally

Create `.env` file in src/ directory:
```
SECRET_KEY=SECRET_KEY
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

#### Option 1: Run with Uvicorn (Direct)
```bash
cd src
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

#### Option 2: Run with Docker

**Build Docker image:**
```bash
docker build -t fastapi-shortened-links .
```

**Run container:**
```bash
docker run -p 8000:10000 \
  -e SECRET_KEY="your_secret_key_here" \
  -e ALGORITHM="HS256" \
  -e ACCESS_TOKEN_EXPIRE_MINUTES="60" \
  fastapi-shortened-links
```

**Access the app:**
- API docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Redis Caching (Optional)

The app includes Redis caching for improved performance on frequently accessed links.

#### Install Redis

**On Windows (using WSL or Docker):**
```bash
docker run -d -p 6379:6379 redis:latest
```

**On Linux/Mac:**
```bash
# macOS (Homebrew)
brew install redis
redis-server

# Linux (Ubuntu/Debian)
sudo apt-get install redis-server
redis-server
```

#### Configure Redis Connection

Set environment variable in `.env`:
```
REDIS_URL=redis://localhost:6379/0
```

Or for Render deployment, use:
```
REDIS_URL=redis://:[PASSWORD]@[HOST]:[PORT]
```

#### How Caching Works

- **Link Access Caching**: When a link is accessed, it's cached in Redis for 1 hour
- **Click Counting**: Click counts are tracked in Redis cache for faster updates
- **Auto-Invalidation**: Cache is cleared when links are updated or deleted
- **Top Links Analytics**: Get the most accessed links via `/analytics/top`

#### New Analytics Endpoint

```bash
GET /analytics/top?limit=10
```

Returns the top 10 most accessed links with click counts (requires authentication)


## API Usage Examples
### 1. Register User
```bash
curl -X POST "link" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "your_name",
    "email": "your_email@example.com",
    "age": int_age
  }'
```
It provides access token (p.2). 

### 2. Create Shortened Link (Auto-Generated)
```bash
curl -X POST "link" \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "original_url": "https://github.com/python/cpython/blob/main/README.rst"
  }'
```

### 3. Create Link with Custom Alias
```bash
curl -X POST "http://localhost:8000/links/shorten" \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "original_url": "https://docs.python.org/3/library/asyncio.html",
    "custom_alias": "python-async"
  }'
```

### 4. Access Shortened Link
```bash
curl -X GET "http://localhost:8000/a3k9xL"
```

### 5. Get Link Statistics
```bash
curl -X GET "http://localhost:8000/links/a3k9xL/stats" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### 6. Update Link
```bash
curl -X PUT "http://localhost:8000/links/a3k9xL" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "original_url": "https://new-url.example.com",
    "expires_at": "2025-04-15T18:00:00"
  }'
```

### 7. Delete Link
```bash
curl -X DELETE "http://localhost:8000/links/a3k9xL" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

Returns 204 No Content on success.

### 8. Search Links
```bash
curl -X GET "http://localhost:8000/links/search?original_url=github.com" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

Returns list of all user's links containing "github.com" in their URL.

### 9. Create Link with Expiration
```bash
curl -X POST "http://localhost:8000/links/shorten" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "original_url": "https://example.com/secret",
    "expires_at": "2025-03-15T23:59:59"
  }'
```
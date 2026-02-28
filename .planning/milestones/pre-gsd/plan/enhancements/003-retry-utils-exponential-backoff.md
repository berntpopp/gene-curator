# Enhancement: RetryUtils with Exponential Backoff and Circuit Breaker

**Priority**: Medium
**Complexity**: Low-Medium
**Estimated Effort**: 3-4 hours
**Reference**: `kidney-genetics-db/backend/app/core/retry_utils.py` (409 lines)

## Overview

Implement advanced retry utilities with exponential backoff, jitter, circuit breaker pattern, and rate limit handling. Eliminate custom retry loops throughout the codebase with a DRY-compliant decorator-based solution.

## Current State

- No unified retry mechanism
- Potential for custom retry loops (error-prone, inconsistent)
- No circuit breaker to prevent cascading failures
- No rate limit handling (429 responses)

## Proposed Implementation

### Core Components

**1. RetryConfig Class** (Configuration)

```python
class RetryConfig:
    """Configuration for retry behavior"""
    max_retries: int = 5
    initial_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    jitter_range: tuple[float, float] = (0.8, 1.2)
    retry_on_exceptions: tuple[type[Exception], ...] = (
        httpx.HTTPStatusError,
        httpx.RequestError,
        httpx.TimeoutException,
    )
    retry_on_status_codes: tuple[int, ...] = (429, 500, 502, 503, 504)

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay with exponential backoff + jitter"""
        delay = min(self.initial_delay * (self.exponential_base ** attempt), self.max_delay)
        if self.jitter:
            delay *= random.uniform(*self.jitter_range)
        return delay
```

**2. CircuitBreaker Class** (Fault tolerance)

```python
class CircuitBreaker:
    """Prevent repeated calls to failing services"""
    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    state: str = "closed"  # closed, open, half-open

    async def async_call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        if self.state == "open":
            if self._should_attempt_reset():
                self.state = "half-open"
            else:
                raise Exception(f"Circuit breaker open (failures: {self.failure_count})")

        try:
            result = await func(*args, **kwargs)
            self._on_success()  # Reset failure count
            return result
        except Exception as e:
            self._on_failure()  # Increment failure count
            raise
```

**3. retry_with_backoff Decorator** (Primary interface)

```python
def retry_with_backoff(
    config: RetryConfig | None = None,
    circuit_breaker: CircuitBreaker | None = None
):
    """Decorator for retrying functions with exponential backoff"""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            for attempt in range(config.max_retries + 1):
                try:
                    if circuit_breaker:
                        return await circuit_breaker.async_call(func, *args, **kwargs)
                    return await func(*args, **kwargs)
                except config.retry_on_exceptions as e:
                    # Special handling for 429 (rate limit)
                    if isinstance(e, httpx.HTTPStatusError) and e.response.status_code == 429:
                        retry_after = e.response.headers.get("retry-after")
                        delay = float(retry_after) if retry_after else config.calculate_delay(attempt)
                    else:
                        delay = config.calculate_delay(attempt)

                    if attempt < config.max_retries:
                        logger.warning(f"Retry {attempt + 1}/{config.max_retries}: {e}")
                        await asyncio.sleep(delay)
                    else:
                        raise

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator
```

**4. RetryableHTTPClient Class** (HTTP-specific)

```python
class RetryableHTTPClient:
    """HTTP client with built-in retry logic"""

    def __init__(
        self,
        client: httpx.AsyncClient,
        retry_config: RetryConfig | None = None,
        circuit_breaker: CircuitBreaker | None = None
    ):
        self.client = client
        self.retry_config = retry_config or RetryConfig()
        self.circuit_breaker = circuit_breaker

    @retry_with_backoff()
    async def get(self, url: str, **kwargs) -> httpx.Response:
        """GET request with automatic retry"""
        response = await self.client.get(url, **kwargs)
        response.raise_for_status()
        return response

    @retry_with_backoff()
    async def post(self, url: str, **kwargs) -> httpx.Response:
        """POST request with automatic retry"""
        response = await self.client.post(url, **kwargs)
        response.raise_for_status()
        return response
```

### Usage Patterns

**Pattern 1: Simple Decorator** (Most Common)

```python
from app.core.retry_utils import retry_with_backoff

# Use default configuration (5 retries, exponential backoff)
@retry_with_backoff()
async def fetch_external_api():
    async with httpx.AsyncClient() as client:
        response = await client.get("https://api.example.com/data")
        response.raise_for_status()
        return response.json()
```

**Pattern 2: Custom Configuration**

```python
from app.core.retry_utils import retry_with_backoff, RetryConfig

# Custom retry behavior
custom_config = RetryConfig(
    max_retries=10,
    initial_delay=2.0,
    max_delay=120.0,
    retry_on_status_codes=(429, 500, 502, 503, 504)
)

@retry_with_backoff(config=custom_config)
async def fetch_rate_limited_api():
    # Automatically handles 429 with Retry-After header
    response = await client.get(url)
    return response.json()
```

**Pattern 3: Circuit Breaker**

```python
from app.core.retry_utils import retry_with_backoff, CircuitBreaker

# Prevent cascading failures
circuit_breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=60.0
)

@retry_with_backoff(circuit_breaker=circuit_breaker)
async def fetch_unreliable_service():
    # After 5 failures, circuit opens for 60 seconds
    response = await client.get(url)
    return response.json()
```

**Pattern 4: RetryableHTTPClient** (Recommended for external APIs)

```python
from app.core.retry_utils import RetryableHTTPClient, RetryConfig

# Reusable HTTP client with retry logic
retry_config = RetryConfig(max_retries=5)
async with httpx.AsyncClient() as base_client:
    client = RetryableHTTPClient(base_client, retry_config=retry_config)

    # All requests automatically retried
    response = await client.get("https://api.example.com/genes")
    genes = response.json()
```

## Implementation Steps

1. **Create retry utils module** (`backend/app/core/retry_utils.py`)
   - Implement RetryConfig class (~60 lines)
   - Implement CircuitBreaker class (~70 lines)
   - Implement retry_with_backoff decorator (~150 lines)
   - Implement RetryableHTTPClient class (~50 lines)

2. **Integrate with existing HTTP calls**
   ```bash
   # Find all external API calls
   rg "httpx\.AsyncClient|requests\.get" backend/app

   # Replace with RetryableHTTPClient or @retry_with_backoff
   ```

3. **Add to dependency injection** (if needed)
   ```python
   # backend/app/core/dependencies.py
   def get_http_client() -> RetryableHTTPClient:
       """Get HTTP client with retry logic"""
       base_client = httpx.AsyncClient(timeout=30.0)
       return RetryableHTTPClient(base_client)
   ```

4. **Update CLAUDE.md** with DRY principle
   ```markdown
   ## Retry Logic (MUST USE)
   - ALWAYS use `@retry_with_backoff()` for external API calls
   - NEVER write custom retry loops (for i in range(5): try/except)
   - Use `RetryableHTTPClient` for HTTP operations
   - Consider circuit breaker for unreliable services
   ```

5. **Add configuration** to settings
   ```python
   # backend/app/core/config.py
   RETRY_MAX_ATTEMPTS: int = 5
   RETRY_INITIAL_DELAY: float = 1.0
   RETRY_MAX_DELAY: float = 60.0
   ```

## Benefits

- **Reliability**: 95%+ success rate for transient failures (proven in production)
- **DRY**: No more scattered retry loops, single decorator interface
- **Fault Tolerance**: Circuit breaker prevents cascading failures
- **Rate Limit Handling**: Automatic Retry-After header parsing
- **Observability**: Structured logging of retry attempts

## Testing

```python
# tests/unit/test_retry_utils.py
import pytest
from unittest.mock import AsyncMock

async def test_retry_success_on_second_attempt():
    """Test successful retry after initial failure"""
    mock_func = AsyncMock(side_effect=[Exception("Fail"), "Success"])

    @retry_with_backoff(config=RetryConfig(max_retries=3))
    async def test_func():
        return await mock_func()

    result = await test_func()
    assert result == "Success"
    assert mock_func.call_count == 2

async def test_circuit_breaker_opens():
    """Test circuit breaker opens after threshold"""
    circuit_breaker = CircuitBreaker(failure_threshold=3)
    mock_func = AsyncMock(side_effect=Exception("Fail"))

    # First 3 attempts fail, then circuit opens
    for i in range(3):
        with pytest.raises(Exception):
            await circuit_breaker.async_call(mock_func)

    assert circuit_breaker.state == "open"

    # Circuit is open, should raise immediately
    with pytest.raises(Exception, match="Circuit breaker open"):
        await circuit_breaker.async_call(mock_func)

async def test_rate_limit_handling():
    """Test automatic Retry-After header parsing"""
    response = httpx.Response(
        status_code=429,
        headers={"retry-after": "2.5"}
    )

    @retry_with_backoff()
    async def test_func():
        raise httpx.HTTPStatusError("Rate limited", request=None, response=response)

    # Should wait 2.5 seconds before retry
    with pytest.raises(httpx.HTTPStatusError):
        await test_func()
```

## Dependencies

- `httpx` - HTTP client library (already in project)
- Standard library: `asyncio`, `time`, `random`, `functools`

## References

- kidney-genetics-db: `backend/app/core/retry_utils.py` (409 lines)
- Production metrics: 95%+ annotation coverage (retry logic fixed coverage issues)
- Error rate: <0.1% with circuit breaker

## Acceptance Criteria

- [ ] RetryConfig, CircuitBreaker, retry_with_backoff implemented
- [ ] RetryableHTTPClient class created
- [ ] At least 5 external API calls refactored to use retry logic
- [ ] Unit tests covering success, failure, circuit breaker scenarios
- [ ] Rate limit handling (429) tested with mock Retry-After header
- [ ] CLAUDE.md updated with DRY retry guidelines
- [ ] Configuration added to backend/app/core/config.py
- [ ] Integration tested with real external API (e.g., HGNC lookup)

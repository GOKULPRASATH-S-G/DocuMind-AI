import time
from typing import Dict, Tuple
from fastapi import Request, HTTPException, status

class RateLimiter:
    """Simple in-memory token bucket rate limiter per client IP / endpoint."""
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.history: Dict[str, list] = {}

    def check_rate_limit(self, key: str):
        now = time.time()
        minute_ago = now - 60.0

        if key not in self.history:
            self.history[key] = []

        # Filter timestamps older than 60s
        self.history[key] = [t for t in self.history[key] if t > minute_ago]

        if len(self.history[key]) >= self.requests_per_minute:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded ({self.requests_per_minute} req/min). Please slow down."
            )

        self.history[key].append(now)

auth_rate_limiter = RateLimiter(requests_per_minute=20)
upload_rate_limiter = RateLimiter(requests_per_minute=30)
rag_rate_limiter = RateLimiter(requests_per_minute=60)
eval_rate_limiter = RateLimiter(requests_per_minute=10)

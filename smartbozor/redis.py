import os

import redis

REDIS_CLIENT = redis.Redis(connection_pool=redis.ConnectionPool(
    host=os.environ.get('REDIS_HOST', '127.0.0.1'),
    port=os.environ.get('REDIS_PORT', 6379),
    db=os.environ.get('REDIS_DB', 0)
))

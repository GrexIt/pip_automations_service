import redis
import json
from .get_actions import GetActions


def automation_enabled(sm_id, redis_host):
    client = redis.Redis(
        host=redis_host, port=6379, decode_responses=True
    )
    sm_key = "sm_id:" + str(sm_id)
    try:
        if client.keys(sm_key) and len(json.loads(client.hget(sm_key, 'priority'))):
            return True
    except Exception:
        pass
    return False


__all__ = ['GetActions']

import redis
import json
from .get_actions import GetActions


def get_redis_client(redis_host):
    return redis.Redis(
        host=redis_host, port=6379, decode_responses=True
    )


def automation_enabled(sm_id, redis_host):
    sm_key = "sm_id:" + str(sm_id)
    client = get_redis_client(redis_host)
    try:
        if client.keys(sm_key) and len(json.loads(client.hget(sm_key, 'priority'))):
            return True
    except Exception:
        pass
    return False


def get_automation_name(sm_id, sm_auto_id, redis_host):
    sm_key = "sm_id:" + str(sm_id)
    client = get_redis_client(redis_host)
    if client.keys(sm_key) and sm_auto_id in json.loads(client.hget(sm_key, 'priority')):
        return json.loads(client.hget(sm_key, 'auto_id:'+str(sm_auto_id)))['name']
    return 'Automation (invalid)'


__all__ = ['GetActions']

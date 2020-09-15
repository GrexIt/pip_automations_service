import redis
import json
from .get_actions import GetActions


def get_redis_client(redis_host):
    return redis.Redis(
        host=redis_host, port=6379, decode_responses=True
    )


def get_automation_name(sm_id, sm_auto_id, redis_host=False, client=False):
    sm_key = "sm_id:" + str(sm_id)
    if not client:
        client = get_redis_client(redis_host)
    if client.keys(sm_key) and sm_auto_id in json.loads(client.hget(sm_key, 'priority')):
        automation_details = client.hget(sm_key, 'auto_id:'+str(sm_auto_id))
        if automation_details:
            return json.loads(automation_details)['name']
    return 'Automation (deleted/disabled)'


def automation_enabled(sm_id, redis_host):
    sm_key = "sm_id:" + str(sm_id)
    client = get_redis_client(redis_host)
    try:
        if client.keys(sm_key):
            priority = json.loads(client.hget(sm_key, 'priority'))
            if len(priority):
                for auto_id in priority:
                    if get_automation_name(sm_id, auto_id, False, client) != 'Automation (deleted/disabled)':
                        return True
    except Exception:
        pass
    return False


__all__ = ['GetActions']

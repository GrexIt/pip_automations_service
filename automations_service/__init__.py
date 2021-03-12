import redis
import json
from .get_actions import GetActions


def get_redis_client(redis_host):
    return redis.Redis(
        host=redis_host, port=6379, decode_responses=True
    )


def get_automation_name(sm_id, sm_auto_id, redis_host=False, client=False, check_for_body_search=False):
    sm_key = "sm_id:" + str(sm_id)
    if not client:
        client = get_redis_client(redis_host)

    if client.keys(sm_key) and sm_auto_id in json.loads(client.hget(sm_key, 'priority')):
        automation_details = client.hget(sm_key, 'auto_id:'+str(sm_auto_id))

        if automation_details:
            auto_detail = json.loads(automation_details)
            if check_for_body_search:
                body_search_automation = False
                if '"property": "body"' in automation_details:
                    body_search_automation = True
                return auto_detail['name'], body_search_automation
            return auto_detail['name']

    deleted_automation_name = 'Automation (deleted/disabled)'
    if check_for_body_search:
        return deleted_automation_name, False
    return deleted_automation_name


def automation_enabled(sm_id, redis_host, check_for_body_search=False):
    sm_key = "sm_id:" + str(sm_id)
    client = get_redis_client(redis_host)
    try:
        if client.keys(sm_key):
            priority = json.loads(client.hget(sm_key, 'priority'))
            if len(priority):
                for auto_id in priority:
                    if check_for_body_search:
                       return get_automation_name(sm_id, auto_id, False, client, check_for_body_search)
                    if get_automation_name(sm_id, auto_id, False, client) != 'Automation (deleted/disabled)':
                        return True
    except Exception:
        pass

    if check_for_body_search:
        return False, False

    return False


__all__ = ['GetActions']

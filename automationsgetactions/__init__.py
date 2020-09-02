import redis


def automation_enabled(sm_id, redis_host):
    client = redis.Redis(
        host=redis_host, port=6379, decode_responses=True
    )

    if not client.keys("sm_id:" + str(sm_id)):
        return False
    return True

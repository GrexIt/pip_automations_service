import json
import re
import redis
from pydantic import BaseModel, Field, conlist
from typing import Union


class AutomationsRedis:
    def __init__(self, redis_host):
        self.client = redis.Redis(
            host=redis_host, port=6379, decode_responses=True
        )

    def hget(self, name, key):
        return self.client.hget(name, key)

    def hset(self, name, key, value):
        return self.client.hset(name, key, value)

    def hgetall(self, name):
        return self.client.hgetall(name)

    def hmset(self, name, dictionary):
        return self.client.hmset(name, dictionary)

    def delete(self, name):
        return self.client.delete(name)


class LogPrint:
    def __init__(self):
        pass

    def debug(self, *argv):
        log = ''
        for arg in argv:
            log += str(arg)
        print(log)


class GetActions:
    """
        Responsible for processesing message_info and returning list of actions
    """

    def __init__(self, payload, redis_host='automations_db', logobj=None):
        print('here')
        self.log = logobj
        if not logobj:
            self.log = LogPrint()
        self.payload = payload
        self.GetActionsRequest = type(self.payload).__name__ == 'GetActionsRequest'
        self.sm_id = self.payload_get('sm_id')
        self.trigger = self.payload_get('trigger')
        self.conditions_payload = self.payload_get('conditions_payload')
        self.log.debug('Get Actions initialized', self.sm_id, self.trigger, self.conditions_payload)
        self.redis = AutomationsRedis(redis_host)

    def payload_get(self, value):
        return getattr(self.payload, value) if self.GetActionsRequest else self.payload[value]

    def process(self):
        self.log.debug('Get Actions process called')
        hmap = self.get_all_automations_from_redis()
        if not hmap:
            return None
        actions = self.get_applicable_automations(hmap)
        if not actions:
            return None
        return actions if self.GetActionsRequest else dict(actions=actions)

    def get_all_automations_from_redis(self):
        return self.redis.hgetall("sm_id:" + str(self.sm_id))

    def get_applicable_automations(self, hmap):
        priority = json.loads(hmap.get("priority"))
        actions = []
        for auto_id in priority:
            automation = json.loads(hmap.get("auto_id:" + str(auto_id)))
            and_flag = 1  # If a single and_condition fails, break out of outer loop
            conditions_json = automation["conditions"]
            for and_condition in conditions_json:
                or_flag = 0  # If  a single or_condition passes, break out of inner loop
                for or_condition in and_condition:
                    if self.does_condition_match(or_condition):
                        or_flag = 1
                        break
                if not or_flag:
                    and_flag = 0
                    break
            if and_flag:  # All conditions passed
                for action in automation["actions"]:
                    actions.append(action)
        return actions

    def does_condition_match(self, or_condition):
        current_property = getattr(self.conditions_payload, or_condition["property"]) if self.GetActionsRequest else self.conditions_payload[or_condition["property"]]
        operator = or_condition["op"]
        condition_values = or_condition["values"]
        if operator == "is":
            return self._is_match(current_property, condition_values[0])
        elif operator == "is not":
            return self._is_match(current_property, condition_values[0], negate=True)
        elif operator == "contains":
            return self._is_regex_match("|".join(condition_values), current_property)
        elif operator == "does not contain":
            return self._is_regex_match(
                "|".join(condition_values), current_property, negate=True
            )
        elif operator == "matches":
            return self._is_regex_match(condition_values[0], current_property)

    def _is_match(self, prop1, prop2, negate=False):
        return (prop1 != prop2) if negate else (prop1 == prop2)

    def _is_regex_match(self, regex, string, negate=False):
        return (
            not bool(re.search(regex, string))
            if negate
            else bool(re.search(regex, string))
        )

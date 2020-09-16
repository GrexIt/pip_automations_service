import json
import re
import redis


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
        log = "\n"
        for arg in argv:
            log += (str(arg)+" ")
            f = open("/usr/src/hiver/logs/backend/json_get_actions.log", "a")
            f.write("Automations " + json.dumps(log))
            f.close()


class GetActions:
    """
        Responsible for processesing message_info and returning list of actions
    """

    def __init__(self, payload, redis_host, logobj=None):
        self.log = logobj
        if not logobj:
            self.log = LogPrint()
        self.payload = payload
        self.GetActionsRequest = type(self.payload).__name__ == 'GetActionsRequest'
        self.sm_id = self.payload_get('smid')
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
            auto_detail = hmap.get("auto_id:" + str(auto_id))
            if not auto_detail:
                continue
            automation = json.loads(auto_detail)
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
                    action['auto_id'] = auto_id
                    actions.append(action)
        return actions

    def escape(self, condition_values):
        values = []
        for condition in condition_values:
            values.append(re.escape(condition))
        return values

    def does_condition_match(self, or_condition):
        match_case = False

        if or_condition["property"] == 'SUBJECT':
            match_case = True
            or_condition["property"] = 'subject'

        current_property = (
            getattr(self.conditions_payload, or_condition["property"])
            if self.GetActionsRequest
            else self.conditions_payload[or_condition["property"]]
        )
        if type(current_property).__name__ not in ['str', 'unicode']:
            current_property = ''

        operator = or_condition["op"]
        condition_values = or_condition["values"]

        if operator == "is":
            current_property = self._sanitize_email(or_condition['property'], current_property)
            return self._is_match(current_property, condition_values[0], match_case, negate=False)
        elif operator == "is not":
            return self._is_match(current_property, condition_values[0], match_case, negate=True)
        elif operator == "contains":
            return self._is_regex_match(
                "|".join(self.escape(condition_values)), current_property, match_case, negate=False
            )
        elif operator == "does not contain":
            return self._is_regex_match(
                "|".join(self.escape(condition_values)), current_property, match_case, negate=True
            )
        elif operator == "matches":
            return self._is_regex_match(condition_values[0], current_property)

    def _sanitize_email(self, prop, value):
        if prop in ['to', 'from']:
            r = re.search('<([^>]+)', value)
            if r:
                return r.group(1)
            else:
                self.log.debug('Automations Error')
        return value

    def _is_match(self, prop1, prop2, match_case=False, negate=False):
        prop1 = str(prop1)
        prop2 = str(prop2)
        if not match_case:
            prop1 = prop1.lower()
            prop2 = prop2.lower()

        return (prop1 != prop2) if negate else (prop1 == prop2)

    def _is_regex_match(self, pattern, string, match_case=False, negate=False):
        matched = self._regex_search(pattern, string, match_case)
        return not bool(matched) if negate else bool(matched)

    def _regex_search(self, pattern, string, match_case):
        if not match_case:
            matched = re.search(pattern, string, re.IGNORECASE)
        else:
            matched = re.search(pattern, string)
        return matched

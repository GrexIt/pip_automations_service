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

    def encode_str(self, value):
        if type(value) == unicode:
            return value.encode('utf-8')
        return value

    def debug(self, *argv):
        log = ""
        for arg in argv:
            log += json.dumps(str(self.encode_str(arg))+" ") + "  "
        f = open("/usr/src/hiver/logs/backend/json_get_actions.log", "a")
        f.write("\nAutomations " + log)
        f.close()
        print("Automations " + log)


class GetActions:
    """
        Responsible for processesing message_info and returning list of actions
    """

    def __init__(self, payload, redis_host, logobj=None, parity_support=False):
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
        self.parity_support = parity_support

    def encode_str(self, value):
        if type(value) == unicode:
            return value.encode('utf-8')
        return value

    def payload_get(self, value):
        return getattr(self.payload, value) if self.GetActionsRequest else self.payload[value]

    def process(self):
        self.log.debug('Get Actions process called', self.payload)
        hmap = self.get_all_automations_from_redis()
        if not hmap:
            return {}
        actions, automations_list = self.get_applicable_automations(hmap)

        if self.GetActionsRequest:
            # Currently unused Flow
            return actions
        return_value = dict(actions=actions, automations_list=automations_list)
        if not self.parity_support:
            return return_value if actions else None
        return return_value

    def get_all_automations_from_redis(self):
        return self.redis.hgetall("sm_id:" + str(self.sm_id))

    def get_applicable_automations(self, hmap):
        priority = json.loads(hmap.get("priority"))
        actions = []
        automations_list = {}
        for auto_id in priority:
            auto_detail = hmap.get("auto_id:" + str(auto_id))
            self.log.debug('Get Actions checking condition', auto_detail)
            if not auto_detail:
                self.log.debug('Get Actions automation disabled/not found')
                continue
            try:
                automation = json.loads(auto_detail)
                automation['id'] = auto_id
                automations_list.update({
                    automation['name'].lower(): automation
                })
                if self.trigger != automation['trigger_name']:
                    self.log.debug('Automations Mismatch in trigger type', self.trigger, automation['trigger_name'])
                    continue
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
            except Exception as e:
                import traceback
                self.log.debug("Automations error in getActions for automation id ", auto_id, traceback.format_exc())
                continue
        return actions, automations_list

    # Alternative for re.escape as it doesn't preserve unicode chars
    def escape(self, condition_values):
        values = []
        for condition in condition_values:
            cond_str = ''
            for char in condition:
                # Escaping ASCII Characters
                if ord(char) < 128:
                    char = re.escape(char)
                # Preseving Unicode Characters
                cond_str += char
            values.append(cond_str)
        return values

    def does_condition_match(self, or_condition):
        match_case = False
        exact_match = False

        if or_condition["property"] in ['SUBJECT', 'BODY']:
            match_case = True
            or_condition["property"] = or_condition["property"].lower()
        elif or_condition["property"] in ['TO', 'CC']:
            exact_match = True
            or_condition["property"] = or_condition["property"].lower()

        current_property = (
            getattr(self.conditions_payload, or_condition["property"])
            if self.GetActionsRequest
            else self.conditions_payload[or_condition["property"]]
        )
        if type(current_property).__name__ not in ['str', 'unicode']:
            current_property = ''

        operator = or_condition["op"]
        condition_values = or_condition["values"]
        current_properties = self._sanitize_data(or_condition['property'], current_property)

        # EXACT MATCH FOR CONTAINS AND DOES NOT CONTAIN
        if exact_match and 'contain' in operator:
            matched = False
            negate_val = (operator == "does not contain")
            for condition_value in condition_values:
                matched = self._is_match(
                    current_properties,
                    condition_value,
                    match_case,
                    negate=False
                )
                if matched:
                    if negate_val:
                        return False
                    return True
            return negate_val

        operator = or_condition["op"]
        condition_values = or_condition["values"]

        # IS clause
        if operator == "is":
            return self._is_match(current_properties, condition_values[0], match_case, negate=False)
        # IS NOT clause
        elif operator == "is not":
            return self._is_match(current_properties, condition_values[0], match_case, negate=True)
        # CONTAINS clause
        elif operator == "contains":
            return self._is_regex_match(
                "|".join(self.escape(condition_values)), ",".join(current_properties), match_case, negate=False
            )
        # CONTAINS NOT clause
        elif operator == "does not contain":
            return self._is_regex_match(
                "|".join(self.escape(condition_values)), ",".join(current_properties), match_case, negate=True
            )
        # MATCHES clause
        elif operator == "matches":
            return self._is_regex_match(condition_values[0], ",".join(current_properties))

    def _sanitize_email(self, value):
        r = re.search('<([^>]+)', value)
        if r:
            return [r.group(1)]
        else:
            self.log.debug('Automations from param not found', value)
            return [value.strip() if value else '']

    def _sanitize_data(self, prop, value):
        if prop in ['from']:
            return self._sanitize_email(value)
        elif prop in ['to', 'cc']:
            email_ids = []
            for email in value.split(','):
                email_ids += self._sanitize_email(email.strip())
            return email_ids
        return [value]

    def _match_case_conversion_required(self, match_case, value):
        self.log.debug('Automations match_case', match_case, value)
        return (not match_case and type(value) in [unicode, str])

    def _is_match(self, current_properties, prop2, match_case=False, negate=False):
        if self._match_case_conversion_required(match_case, prop2):
            prop2 = prop2.lower()
        prop2 = str(self.encode_str(prop2))

        for prop1 in current_properties:
            if self._match_case_conversion_required(match_case, prop1):
                prop1 = prop1.lower()
            prop1 = str(self.encode_str(prop1))
            self.log.debug('Automations comparison', prop1, prop2, negate, match_case)
            if prop1 == prop2:
                if negate:
                    return False
                else:
                    return True

        return negate

    def _is_regex_match(self, pattern, string, match_case=False, negate=False):
        if not match_case:
            string = string.lower()
            pattern = pattern.lower()

        matched = re.search(pattern, string)
        return not bool(matched) if negate else bool(matched)

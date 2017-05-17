"""Property wrappers handling potentially obsolete formats..."""
from aomi.helpers import warning
from aomi.vault import app_id_name


def app_id_itself(app_obj, data):
    """Determines the application ID to use"""
    app_id = None
    if 'app_id' in data:
        warning('Defining app_id within the app yaml is deprecated')
        app_id = data['app_id']
    elif 'app_id' in app_obj:
        app_id = app_obj['app_id']
    else:
        app_id = app_id_name(app_obj)

    return app_id


def app_id_policy_file(app_obj, data):
    """Determines the correct policy file name, checking both the
    proper and legacy location"""
    policy_file = None
    if 'policy' in data:
        warning('Defining policy_name within the app yaml is deprecated')
        policy_file = data['policy']
    elif 'policy' in app_obj:
        policy_file = app_obj['policy']

    return policy_file


def app_id_policy_name(app_obj, data):
    """Determines the policy name, checking both the proper
    and the legacy location"""
    policy_name = None
    if 'policy_name' in data:
        warning('Defining policy_name within the app yaml is deprecated')
        policy_name = data['policy_name']
    elif 'policy_name' in data:
        policy_name = app_obj['policy_name']
    else:
        policy_name = app_id_name(app_obj)

    return policy_name

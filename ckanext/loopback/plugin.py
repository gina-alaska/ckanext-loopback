import logging
import requests
import pylons
import json
import ckan.plugins as plugins
import ckan.logic as logic
import ckan.lib.navl.dictization_functions
import ckan.lib.dictization.model_dictize as model_dictize
import ckan.lib.dictization.model_save as model_save

log = logging.getLogger(__name__)
_validate = ckan.lib.navl.dictization_functions.validate
_get_action = logic.get_action
_check_access = logic.check_access
ValidationError = logic.ValidationError
_get_or_bust = logic.get_or_bust
_group_or_org_create = logic.action.create._group_or_org_create
_group_or_org_member_create = logic.action.create._group_or_org_member_create
_group_or_org_member_delete = logic.action.delete._group_or_org_member_delete

def loopback_login():
    loopback_login_url = pylons.config.get('ckan.loopback.login_url')

    response = requests.post(loopback_login_url, data = {
        'username': pylons.config.get('ckan.loopback.username'),
        'password': pylons.config.get('ckan.loopback.password')
    })

    response.raise_for_status()

    pylons.config['loopback_token'] = json.loads(response.text)['id']
    log.debug('Logged into LoopBack with access token: {}'
        .format(pylons.config.get('loopback_token')))

def loopback_user_create(user_info):
    if pylons.config.get('loopback_token') is None:
        loopback_login()

    loopback_user_url = pylons.config.get('ckan.loopback.user_url')
    loopback_token = pylons.config.get('loopback_token')
    request_url = '{}?access_token={}'.format(loopback_user_url, loopback_token)
    response = requests.post(request_url, data = user_info)

    if response.status_code == 401:
        loopback_login()
    else:
        response.raise_for_status()

    log.debug('LoopBack user created: {}'.format(user_info['id']))

def loopback_user_update(id, user_info):
    if pylons.config.get('loopback_token') is None:
        loopback_login()

    loopback_user_url = pylons.config.get('ckan.loopback.user_url')
    loopback_user_id_url = '{}/{}'.format(loopback_user_url, id)
    loopback_token = pylons.config.get('loopback_token')
    request_url = '{}?access_token={}'.format(loopback_user_id_url, loopback_token)
    response = requests.put(request_url, data = user_info)

    if response.status_code == 401:
        loopback_login()
    else:
        response.raise_for_status()

    log.debug('LoopBack user updated: {}'.format(id))

def loopback_group_create(group_info):
    if pylons.config.get('loopback_token') is None:
        loopback_login()

    loopback_user_url = pylons.config.get('ckan.loopback.group_url')
    loopback_token = pylons.config.get('loopback_token')
    request_url = '{}?access_token={}'.format(loopback_user_url, loopback_token)
    response = requests.post(request_url, data = group_info)

    if response.status_code == 401:
        loopback_login()
    else:
        response.raise_for_status()

    log.debug('LoopBack group created: {}'.format(group_info['id']))

# Taken from ckan/logic/action/create.py and adapted to add LoopBack parts.
def user_create(context, data_dict):
    model = context['model']
    schema = context.get('schema') or ckan.logic.schema.default_user_schema()
    session = context['session']

    _check_access('user_create', context, data_dict)

    data, errors = _validate(data_dict, schema, context)

    if errors:
        session.rollback()
        raise ValidationError(errors)

    if 'password_hash' in data:
        data['_password'] = data.pop('password_hash')

    user = model_save.user_dict_save(data, context)

    if user.email == pylons.config.get('ckan.loopback.email'):
        raise ValidationError({'Email Address': ['Invalid email address.']})

    session.flush()

    loopback_user_create({
        'id': user.id,
        'username': user.name,
        'email': user.email,
        'password': data['password']
    })

    activity_create_context = {
        'model': model,
        'user': context['user'],
        'defer_commit': True,
        'ignore_auth': True,
        'session': session
    }
    activity_dict = {
        'user_id': user.id,
        'object_id': user.id,
        'activity_type': 'new user',
    }
    logic.get_action('activity_create')(activity_create_context, activity_dict)

    if not context.get('defer_commit'):
        model.repo.commit()

    user_dictize_context = context.copy()
    user_dictize_context['keep_apikey'] = True
    user_dictize_context['keep_email'] = True
    user_dict = model_dictize.user_dictize(user, user_dictize_context)

    context['user_obj'] = user
    context['id'] = user.id

    model.Dashboard.get(user.id)

    log.debug('CKAN user created: {}'.format(user.name))
    return user_dict

# Taken from ckan/logic/action/update.py and adapted to add LoopBack parts.
def user_update(context, data_dict):
    model = context['model']
    user = context['user']
    session = context['session']
    schema = context.get('schema') or schema_.default_update_user_schema()
    id = _get_or_bust(data_dict, 'id')

    user_obj = model.User.get(id)
    context['user_obj'] = user_obj
    if user_obj is None:
        raise NotFound('User was not found.')

    _check_access('user_update', context, data_dict)

    data, errors = _validate(data_dict, schema, context)
    if errors:
        session.rollback()
        raise ValidationError(errors)

    if 'password_hash' in data:
        data['_password'] = data.pop('password_hash')

    user = model_save.user_dict_save(data, context)

    if user.name == pylons.config.get('ckan.loopback.username'):
        raise ValidationError({'Username': ['Invalid username.']})

    loopback_user_info = {
        'username': user.name,
        'email': user.email
    }

    if 'password' in data:
        loopback_user_info['password'] = data['password']

    loopback_user_update(user.id, loopback_user_info)

    activity_dict = {
            'user_id': user.id,
            'object_id': user.id,
            'activity_type': 'changed user',
            }
    activity_create_context = {
        'model': model,
        'user': user,
        'defer_commit': True,
        'ignore_auth': True,
        'session': session
    }
    _get_action('activity_create')(activity_create_context, activity_dict)

    if not context.get('defer_commit'):
        model.repo.commit()

    log.debug('CKAN user updated: {}'.format(user.name))
    return model_dictize.user_dictize(user, context)

# Taken from ckan/logic/action/create.py and adapted to add LoopBack parts.
def organization_create(context, data_dict):
    data_dict.setdefault('type', 'organization')
    _check_access('organization_create', context, data_dict)

    organization = _group_or_org_create(context, data_dict, is_org=True)

    loopback_group_create({
      'id': organization['id'],
      'name': organization['title']
    })

    return organization

# Taken from ckan/logic/action/create.py and adapted to add LoopBack parts.
def organization_member_create(context, data_dict):
    _check_access('organization_member_create', context, data_dict)
    member = _group_or_org_member_create(context, data_dict, is_org=True)

    loopback_user_update(member['table_id'], {
      'groupId': context['group'].id
    })

    return member

# Taken from ckan/logic/action/delete.py and adapted to add LoopBack parts.
def organization_member_delete(context, data_dict=None):
    _check_access('organization_member_delete',context, data_dict)

    loopback_user_info = {
        'groupId': ''
    }

    loopback_user_update(data_dict['user_id'], loopback_user_info)

    return _group_or_org_member_delete(context, data_dict)

class LoopbackPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IActions)

    def get_actions(self):
        return {
            'user_create': user_create,
            'user_update': user_update,
            'organization_create': organization_create,
            'organization_member_create': organization_member_create,
            'organization_member_delete': organization_member_delete
        }

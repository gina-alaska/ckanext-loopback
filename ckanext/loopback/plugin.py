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

def loopback_login():
    # Get the base URL for the LoopBack user model.
    loopback_user_url = pylons.config.get('ckan.loopback.login_url')

    response = requests.post(loopback_user_url, data = {
        'username': pylons.config.get('ckan.loopback.username'),
        'password': pylons.config.get('ckan.loopback.password')
    })

    response.raise_for_status()

    # TODO: Find a better place to store the LoopBack token.
    # No need to have a separate LoopBack token for each browser session.
    pylons.session['loopback_token'] = json.loads(response.text)['id']
    pylons.session.save()
    log.debug('Logged into LoopBack with access token: {}'
        .format(pylons.session.get('loopback_token')))

def loopback_user_create(user_info):
    if pylons.session.get('loopback_token') is None:
        loopback_login()

    loopback_user_url = pylons.config.get('ckan.loopback.user_url')
    loopback_token = pylons.session.get('loopback_token')
    request_url = '{}?access_token={}'.format(loopback_user_url, loopback_token)
    response = requests.post(request_url, data = user_info)
    response.raise_for_status()
    log.debug('LoopBack user created: {}'.format(user_info['username']))

def loopback_user_update(id, user_info):
    if pylons.session.get('loopback_token') is None:
        loopback_login()

    loopback_user_url = pylons.config.get('ckan.loopback.user_url')
    loopback_user_id_url = '{}/{}'.format(loopback_user_url, id)
    loopback_token = pylons.session.get('loopback_token')
    request_url = '{}?access_token={}'.format(loopback_user_id_url, loopback_token)
    response = requests.put(request_url, data = user_info)
    response.raise_for_status()
    log.debug('LoopBack user updated: {}'.format(user_info['username']))

# Copy and pasted from CKAN core except for LoopBack parts.
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

    session.flush()

    loopback_user_create({
        'id': user.id,
        'username': user.name,
        'email': user.email,
        'apikey': user.apikey,
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

# Copy and pasted from CKAN core except for LoopBack parts.
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

    loopback_user_info = {
        'username': user.name,
        'email': user.email,
        'apikey': user.apikey
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

class LoopbackPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IActions)

    def get_actions(self):
        return {
            'user_create': user_create,
            'user_update': user_update
        }

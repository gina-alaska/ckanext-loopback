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

def loopback_user_create(credentials):
    loopback_user_url = pylons.config.get('ckan.loopback.user_url')
    response = requests.post(loopback_user_url, data = credentials)
    response.raise_for_status()
    loopback_login(credentials)

def loopback_login(credentials):
    loopback_user_url = pylons.config.get('ckan.loopback.login_url')
    response = requests.post(loopback_user_url, data = {
        'username': credentials['username'],
        'password': credentials['password']
    })
    pylons.session['loopback_token'] = json.loads(response.text)['id']
    pylons.session.save()

# Adapted from CKAN core.
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

    log.debug('Created user {name}'.format(name=user.name))
    return user_dict

class LoopbackPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IActions)

    def get_actions(self):
        return {
            'user_create': user_create
        }

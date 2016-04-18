# Copyright (c) 2016 Catalyst IT Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import collections
import json
import logging
import requests
import urlparse

from django.conf import settings

from openstack_dashboard.api import base

LOG = logging.getLogger(__name__)
USER = collections.namedtuple('User',
                              ['id', 'name', 'email',
                               'roles', 'cohort', 'status'])
TOKEN = collections.namedtuple('Token',
                               ['action'])


def _get_endpoint_url(request):
    # If the request is made by an anonymous user, this endpoint request fails.
    # Thus, we must hardcode this in Horizon.
    if getattr(request.user, "service_catalog", None):
        url = base.url_for(request, service_type='registration')
    else:
        url = getattr(settings, 'OPENSTACK_REGISTRATION_URL')

    # Ensure ends in slash
    if not url.endswith('/'):
        url += '/'

    return url


def _request(request, method, url, headers, **kwargs):
    try:
        endpoint_url = _get_endpoint_url(request)
        url = urlparse.urljoin(endpoint_url, url)
        session = requests.Session()
        data = kwargs.pop("data", None)
        return session.request(method, url, headers=headers,
                               data=data, **kwargs)
    except Exception as e:
        LOG.error(e)
        raise


def head(request, url, **kwargs):
    return _request(request, 'HEAD', url, **kwargs)


def get(request, url, **kwargs):
    return _request(request, 'GET', url, **kwargs)


def post(request, url, **kwargs):
    return _request(request, 'POST', url, **kwargs)


def put(request, url, **kwargs):
    return _request(request, 'PUT', url, **kwargs)


def patch(request, url, **kwargs):
    return _request(request, 'PATCH', url, **kwargs)


def delete(request, url, **kwargs):
    return _request(request, 'DELETE', url, **kwargs)


def user_invite(request, user):
    headers = {'Content-Type': 'application/json',
               'X-Auth-Token': request.user.token.id}
    user['project_id'] = request.user.tenant_id
    return post(request, 'openstack/users',
                headers=headers, data=json.dumps(user))


def user_list(request):
    users = []
    try:
        headers = {'Content-Type': 'application/json',
                   'X-Auth-Token': request.user.token.id}
        resp = json.loads(get(request, 'openstack/users',
                              headers=headers).content)

        for user in resp['users']:
            users.append(
                USER(
                    id=user['id'],
                    name=user['name'],
                    email=user['email'],
                    roles=user['roles'],
                    status=user['status'],
                    cohort=user['cohort']
                )
            )
    except Exception as e:
        LOG.error(e)
        raise
    return users


def user_get(request, user_id):
    try:
        headers = {'X-Auth-Token': request.user.token.id}
        resp = get(request, 'openstack/users/%s' % user_id,
                   headers=headers).content
        return json.loads(resp)
    except Exception as e:
        LOG.error(e)
        raise


def user_roles_update(request, user):
    try:
        headers = {'Content-Type': 'application/json',
                   'X-Auth-Token': request.user.token.id}
        user['project_id'] = request.user.tenant_id
        user['roles'] = user.roles
        return put(request, 'openstack/users/%s/roles' % user['id'],
                   headers=headers,
                   data=json.dumps(user))
    except Exception as e:
        LOG.error(e)
        raise


def user_roles_add(request, user_id, roles):
    try:
        headers = {'Content-Type': 'application/json',
                   'X-Auth-Token': request.user.token.id}
        params = {}
        params['project_id'] = request.user.tenant_id
        params['roles'] = roles
        return put(request, 'openstack/users/%s/roles' % user_id,
                   headers=headers,
                   data=json.dumps(params))
    except Exception as e:
        LOG.error(e)
        raise


def user_roles_remove(request, user_id, roles):
    try:
        headers = {'Content-Type': 'application/json',
                   'X-Auth-Token': request.user.token.id}
        params = {}
        params['project_id'] = request.user.tenant_id
        params['roles'] = roles
        return delete(request, 'openstack/users/%s/roles' % user_id,
                      headers=headers,
                      data=json.dumps(params))
    except Exception as e:
        LOG.error(e)
        raise


def user_revoke(request, user_id):
    try:
        headers = {'Content-Type': 'application/json',
                   'X-Auth-Token': request.user.token.id}
        data = dict()
        return delete(request, 'openstack/users/%s' % user_id,
                      headers=headers,
                      data=json.dumps(data))
    except Exception as e:
        LOG.error(e)
        raise


def user_invitation_resend(request, user_id):
    headers = {'Content-Type': 'application/json',
               'X-Auth-Token': request.user.token.id}
    # For non-active users, the task id is the same as their userid
    # For active users, re-sending an invitation doesn't make sense.
    data = {
        "task": user_id
    }
    return post(request, 'tokens',
                headers=headers,
                data=json.dumps(data))


def valid_roles_get(request):
    headers = {'Content-Type': 'application/json',
               'X-Auth-Token': request.user.token.id}
    role_data = get(request, 'openstack/roles', headers=headers)
    return role_data.json()


def valid_role_names_get(request):
    roles_data = valid_roles_get(request)
    role_names = [r['name'] for r in roles_data['roles']]
    return role_names


def token_get(request, token, data):
    headers = {'Content-Type': 'application/json'}
    return get(request, 'tokens/%s' % token,
               data=json.dumps(data), headers=headers)


def token_submit(request, token, data):
    headers = {"Content-Type": "application/json"}
    return post(request, 'tokens/%s' % token,
                data=json.dumps(data), headers=headers)


def forgotpassword_submit(request, email, username=None):
    # Username is optional only if the registration API considers it so
    # In this case the backend assumes email==username
    headers = {"Content-Type": "application/json"}
    data = {
        'email': email
    }
    if username:
        data['username'] = username
    try:
        return post(request, 'openstack/users/password-reset',
                    data=json.dumps(data),
                    headers=headers)
    except Exception as e:
        LOG.error(e)
        raise

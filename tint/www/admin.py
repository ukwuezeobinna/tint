from __future__ import unicode_literals
from tint.tint.central.utils import enable_site
from tint.tint.central.clients import verify_access_request
from tint.tint.central.utils import get_query_params
import frappe
from frappe import _
import re
from tint.tint.central.api import get_site_details, update_doc
from tint.events.auth import successful_login
from frappe.utils.password import update_password
# from frappe.desk.page.setup_wizard.setup_wizard import add_all_roles_to

no_cache = 1


def get_context(context):
    site = frappe.local.site
    # enable_site()

    context.site = site
    central_site = frappe.conf.get('central_api_url')
    url = frappe.request.url
    query_params = get_query_params(url)

    msg = 'Please wait a sec...'
    context.msg = msg
    # if the site is central, skip
    if re.search(rf'{site}', central_site, flags=re.IGNORECASE):
        context.msg = 'Redirecting to login...'
        context.central = True
        return
    if not query_params:
        context.msg = 'Invalid request, no role or access key provided'
        # return
    elif not query_params.get('role'):
        context.msg = 'Invalid request, role not provided'
        # return
    elif not query_params.get('k'):
        context.msg = 'Invalid request, access key not provided'
    elif not query_params.get('u'):
        context.msg = 'Invalid request, user not provided'
    else:
        # # context.auth = f'token {api_key}'
        key = query_params.get('k')
        user = query_params.get('u')
        role = query_params.get('role')
        if user == frappe.session.user:
            context.msg = 'Already logged in... Redirecting'
            context.redirect_to_desk = True
            context.access_granted = True

        allow_access = verify_access_request(user=user, access_key=key, role=role)
        # print('allow access', allow_access, user, allow_access.get('success'))
        if not allow_access:
            context.msg = 'An error occurred during request. Please try again later' if not allow_access.get(
                'errMsg') else allow_access['errMsg']
            context.redirect_to_desk = False
            context.access_granted = False
        elif allow_access.get('success') and allow_access.get('access') == True:
            role_name = f'Site {role}' if role != 'Administrator' else 'Administrator'
            manager_roles_map = {
                "Site HR Manager": {
                    "role": "HR Manager",
                    "email": "hr_manager@chimso.xyz",
                },
                "Site Payroll Manager": {
                    "role": "Payroll Manager",
                    "email": "payroll_manager@chimso.xyz",
                },
                "Site Auditor": {
                    "role": "Auditor",
                    "email": "auditor@chimso.xyz",
                },
            }
            if role != 'Administrator':
                email = manager_roles_map.get(role_name)['email']
            else:
                email = role
            username = frappe.db.get_value('User', email, 'name')
            if not username:
                context.msg = 'Error, user {} ({}) not found'.format(role, email)
                return
            # print('user', username, email)
            frappe.local.login_manager.login_as(username)
            # enable_site()
            context.redirect_to_desk = True
            context.access_granted = True
        else:
            context.msg = 'Access denied, verification failed. Please try again later' if not allow_access.get('errMsg') else allow_access['errMsg']
            context.redirect_to_desk = False
            context.access_granted = False


    



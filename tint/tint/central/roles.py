import json
import os
from central.central.utils import get_common_config
from tint.tint.utils import update_key_on_proxy
import frappe
from frappe import _
from frappe.utils import random_string
from frappe.utils import password
from frappe.utils.password import update_password as _update_password
from tint.tint.central.utils import get_site_config
from frappe.permissions import add_permission, update_permission_property


@frappe.whitelist()
def create_inter_site_user(role, permissions=[], user_data={}):
    """
    To create manager(admin) roles/user sites via api from central
    """
    print('role to create', role, user_data, frappe.db.exists('Role', role))
    # check if the role exists
    if not frappe.db.exists('Role', role):
        initialize_role(role)
    # create user and assign role
    return create_admin_user(user_data=user_data, roles=[role], name=role)


def initialize_role(role, desk_access=1):
    """
    To create the role, eg Sales Partner if it does not exist
    """
    if frappe.db.exists("Role", {"role_name": role}):
        print(f"Rolen {role} already exists...")
        return
    role = frappe.get_doc(
        {'doctype': 'Role', 'role_name': role, 'desk_access': desk_access})
    try:
        role.insert(ignore_permissions=True)
        print('{} Role created successfully'.format(role.role_name))
    except frappe.DuplicateEntryError as e:
        print('Role creation failed for {}'.format(role.role_name),
              e.message if hasattr(e, 'message') else e)
    except:
        print('Role creation failed for {}'.format(role.role_name))


def create_admin_user(user_data, name=None, roles=[]):
    user_data = json.loads(user_data)
    full_name = user_data.get("full_name") or name
    print('user data', user_data, isinstance(user_data, str),
          frappe.db.exists("User", {"full_name": full_name}))
    if frappe.db.exists("User", {"full_name": full_name}):
        user = frappe.get_doc('User', {"full_name": full_name})
        print('user exists', user.name, roles)
        for role in roles:
            user.append(
                "roles", {
                    "doctype": "Has Role",
                    "role": role
                }
            )
            user.save(ignore_permissions=True)
        return {'success': True, 'error': False, 'msg': 'User already exists'}
    password = user_data.get('password') or random_string(20)
    user = frappe.get_doc({
        "doctype": "User",
        "email": user_data.get('email') or "support@chimso.xyz",
        "first_name": full_name,
        "enabled": 1,
        "short_bio": "User attempting to sign up for site",
        "mobile_no": user_data.get('mobile_no'),
        "new_password": password,
        "send_welcome_email": 0,
        "user_type": "System User"
    })

    print('user', user.name, user.as_json())
    user.flags.ignore_permissions = True
    user.flags.ignore_password_policy = True
    try:
        user.insert()
    except frappe.exceptions.UniqueValidationError as e:
        print('unique value error', e)
        return {'status': 'failed', 'error': True, 'errMsg': e, 'msg': "", 'user': user.name}
    except:
        return {'status': 'failed', 'error': True, 'errMsg': 'Error occured while trying to create user', 'msg': "", 'user': user.name}
    # Update the password
    _update_password(user=user.name, pwd=password,
                     logout_all_sessions=user.logout_all_sessions)

    # set default signup role as per Portal Settings
    default_role = frappe.db.get_value(
        "Portal Settings", None, "default_role")
    if default_role:
        user.add_roles(default_role)
    for role in roles:
        user.append(
            "roles", {
                "doctype": "Has Role",
                "role": role
            }
        )
    user.save(ignore_permissions=True)
    return {'success': True, 'error': False, 'msg': 'User {} created successfully on {}'.format(user, frappe.local.site), 'user': user}

def update_common_config(key, value, validate=True, sites_path=None):
	"""Update a value in site_config"""
	sites_path = frappe.local.sites_path
	config = {}
	common_site_config_path = ''

	if sites_path:
		common_site_config_path = os.path.join(sites_path, "common_site_config.json")

	with open(common_site_config_path, "r") as f:
		config = json.loads(f.read())

	# In case of non-int value
	if value in ('0', '1'):
		value = int(value)

	# boolean
	if value == 'false':
		value = False
	if value == 'true':
		value = True

	# remove key if value is None
	if value == "None":
		if key in config:
			del config[key]
	else:
		config[key] = value

	with open(common_site_config_path, "w") as f:
		f.write(json.dumps(config, indent=1, sort_keys=True))

	if hasattr(frappe.local, "conf"):
		frappe.local.conf[key] = value

def update_site_config(key, value, validate=True, sites_path=None):
    """Update a value in site_config"""
    sites_path = frappe.local.sites_path
    site_config_path = ''

    if sites_path:
        site_config_path = os.path.join(
            sites_path, frappe.local.site, "site_config.json")

    print(f'config path {site_config_path}')
    config = get_site_config()

    # In case of non-int value
    if value in ('0', '1'):
        value = int(value)

    # boolean
    if value == 'false':
        value = False
    if value == 'true':
        value = True

    # remove key if value is None
    if value == "None":
        if key in config:
            del config[key]
    else:
        config[key] = value

    with open(site_config_path, "w") as f:
        f.write(json.dumps(config, indent=1, sort_keys=True))

    if hasattr(frappe.local, "conf"):
        frappe.local.conf[key] = value


@frappe.whitelist()
def generate_keys(user):
    """
    generate api key and api secret

    :param user: str
    """
    site = frappe.local.site
    # print(frappe.session.user, config.get('admin_auth_key'))
    if "System Manager" in frappe.get_roles():
        user_details = frappe.get_doc("User", user)
        api_secret = frappe.generate_hash(length=15)
        # if api key is not set generate api key
        if not user_details.api_key:
            api_key = frappe.generate_hash(length=15)
            user_details.api_key = api_key
        user_details.api_secret = api_secret
        # To ensure the user is enabled
        if user_details.enabled == 0:
            user_details.enabled = 1
        user_details.save()
        auth_key = f"{user_details.api_key}:{api_secret}"

        # if user == 'Administrator':print("Auth key", auth_key)
        print("api_key", auth_key)
        if user == 'Administrator':
            update_site_config("api_key", auth_key)
            if frappe.local.site == get_common_config().get('central_api_url', ''): update_common_config("admin_auth_key", auth_key)

        return {"api_secret": api_secret, 'success': True, "auth_key": auth_key, 'error': False, 'msg': 'Api keys for {user} created successfully for {site}'.format(user=user, site=site)}
    frappe.throw(frappe._("Not Permitted. Access Denied"),
                 frappe.PermissionError)


@frappe.whitelist(allow_guest=True)
def generate_admin_keys():
    print('Generating Admin API keys...')
    res = generate_keys('Administrator')
    print('API keys generated successfully and saved')
    if frappe.conf.get("webhook_url"):
        update_key_on_proxy(res.get('auth_key'))
    return res


def add_roles(user, *roles):
    print(f'Adding roles to user', *roles)
    user = frappe.get_doc('User', user)
    user.add_roles(*roles)


def remove_roles(user, *roles):
    user = frappe.get_doc('User', user)
    user.remove_roles(*roles)


@frappe.whitelist()
def add_permission_for_role(doctype, ptype, permlevel=0, role="All"):
    """To add permission of a role for a doctype"""
    try:
        add_permission(
            doctype=doctype, role=role, permlevel=permlevel, ptype=ptype)
        return True
    except Exception as e:
        print("Error!!!", e)
        return False


@frappe.whitelist()
def update_permission_for_role(doctype, ptype, value, permlevel=0, role="All"):
    """To update permission of a role for a doctype"""
    try:
        update_permission_property(
            doctype=doctype, role=role, permlevel=permlevel, ptype=ptype, value=value)
        return True
    except Exception as e:
        print("Error!!!", e)
        return False


def initialize_role(role, desk_access=1):
    """
    To create the role, eg Sales Partner if it does not exist
    """
    if frappe.db.exists("Role", {"role_name": role}):
        print(f"Role {role} already exists...")
        return
    role = frappe.get_doc(
        {'doctype': 'Role', 'role_name': role, 'desk_access': desk_access})
    try:
        role.insert(ignore_permissions=True)
        print('{} Role created successfully'.format(role.role_name))
    except frappe.DuplicateEntryError as e:
        print('Role creation failed for {}'.format(role.role_name),
              e.message if hasattr(e, 'message') else e)
    except:
        print('Role creation failed for {}'.format(role.role_name))


@frappe.whitelist()
def add_role_permission(doctype, role, ptype, permlevel=0, value=0):
    add_permission(doctype=doctype, role=role)
    update_permission_property(
        doctype=doctype, role=role, permlevel=permlevel, ptype=ptype, value=value)

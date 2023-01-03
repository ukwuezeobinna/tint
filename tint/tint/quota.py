import frappe
from frappe.utils.data import today, add_days
import json
import subprocess
import os
from frappe.utils import cint
from frappe import _
from frappe.installer import update_site_config
from tint.events.auth import site_is_exempted


def user_limit(self, method):
    # check if site is exempted
    # if not check if quota has been initialized
    parsed = {}
    try:
        if site_is_exempted() or check_if_quota_exists() == False:
            raise FileNotFoundError
        with open(frappe.get_site_path('quota.json')) as jsonfile:
            parsed = json.load(jsonfile)
    # bypass sites with no quota file
    except FileNotFoundError:
        return
    count_website_users = parsed["count_website_users"]
    count_administrator_user = parsed["count_administrator_user"]
    allowed_users = parsed["users"]

    active_users = validate_users(
        self, count_administrator_user, count_website_users, allowed_users)

    data = {}
    with open(frappe.get_site_path('quota.json')) as outfile:
        data = json.load(outfile)
    data['active_users'] = active_users

    with open(frappe.get_site_path('quota.json'), 'w') as outfile:
        json.dump(data, outfile, indent=2)


def files_space_limit(self, method):
    if site_is_exempted():
        return
    validate_files_space_limit()


def validate_files_space_limit():
    try:
        if site_is_exempted() or check_if_quota_exists() == False:
            raise FileNotFoundError
        with open(frappe.get_site_path('quota.json')) as jsonfile:
            parsed = json.load(jsonfile)
    # bypass sites with no quota file
    except FileNotFoundError:
        return
    allowed_space = parsed["space"]

    site_path = frappe.get_site_path()
    private_files_path = site_path + '/private/files'
    public_files_path = site_path + '/public/files'
    backup_files_path = site_path + '/private/backups'

    # Calculating Sizes
    total_size = get_directory_size(site_path)
    private_files_size = get_directory_size(private_files_path)
    public_files_size = get_directory_size(public_files_path)
    backup_files_size = get_directory_size(backup_files_path)

    parsed['used_space'] = total_size
    parsed['private_files_size'] = private_files_size
    parsed['public_files_size'] = public_files_size
    parsed['backup_files_size'] = backup_files_size

    with open(frappe.get_site_path('quota.json'), 'w') as outfile:
        json.dump(parsed, outfile, indent=2)

    if total_size > allowed_space:
        msg = '<div>You have exceeded your files space limit. Delete some files from file manager or to incease the limit please contact sales</div>'
        msg += '<div><ul><li>Private Files: {}MB</li><li>Public Files: {}MB</li><li>Backup Files: {}MB</li></ul></div>'.format(
            private_files_size, public_files_size, backup_files_size)
        frappe.throw(_(msg))


def db_space_limit(self, method):
    validate_db_space_limit()


def validate_db_space_limit():
    try:
        if site_is_exempted() or check_if_quota_exists() == False:
            raise FileNotFoundError
        with open(frappe.get_site_path('quota.json')) as jsonfile:
            parsed = json.load(jsonfile)
    # bypass sites with no quota file
    except FileNotFoundError:
        return
    allowed_db_space = parsed["db_space"]
    used_db_space = frappe.db.sql(
        '''SELECT `table_schema` as `database_name`, SUM(`data_length` + `index_length`) / 1024 / 1024 AS `database_size` FROM information_schema.tables  GROUP BY `table_schema`''')[1][1]
    used_db_space = int(used_db_space)
    parsed['used_db_space'] = used_db_space

    with open(frappe.get_site_path('quota.json'), 'w') as outfile:
        json.dump(parsed, outfile, indent=2)

    if used_db_space > allowed_db_space:
        msg = '<div>You have exceeded your Database Size Limit. Please contact sales to upgrade your package</div>'
        msg += '<ul><li>Allowed Space: {}MB</li><li>Used Space: {}MB</li></ul>'.format(
            allowed_db_space, used_db_space)
        frappe.throw(_(msg))


def company_limit(self, method):
    try:
        if site_is_exempted() or check_if_quota_exists() == False:
            raise FileNotFoundError
        with open(frappe.get_site_path('quota.json')) as jsonfile:
            limit_setting = json.load(jsonfile)
    # bypass sites with no quota file
    except FileNotFoundError:
        return

    total_company = len(frappe.db.get_all('Company', filters={}))

    if total_company >= cint(limit_setting.get('company')):
        if not frappe.get_list('Company', filters={
            'name': self.name
        }):
            frappe.throw(_("Only {} company allowed and you have {} company.Please remove other company or to increase the limit please contact sales").format(
                limit_setting.get('company'), total_company))

    with open(frappe.get_site_path('quota.json')) as outfile:
        data = json.load(outfile)
        data['used_company'] = total_company
    with open(frappe.get_site_path('quota.json'), 'w') as outfile:
        json.dump(data, outfile, indent=2)


def validate_users(self, count_administrator_user, count_website_users, allowed_users):
    '''
    validates and returns active users
    '''
    if site_is_exempted():
        return

    # Fetching user list
    filters = {}
    if count_administrator_user == 0:
        filters = {
            'enabled': 1,
            'name': ['!=', 'Guest', 'Administrator']
        }
    else:
        filters = {
            'enabled': 1,
            'name': ['!=', 'Guest']
        }
    user_list = frappe.get_list('User', filters=filters, fields=["name"])

    active_users = 0
    # Validating if website users are to be counted or not
    if count_website_users == 1:
        active_users = len(user_list)
    else:
        for user in user_list:
            if user.name == 'Administrator' and count_administrator_user == 0:
                continue

            roles = frappe.get_list("Has Role", filters={
                'parent': user.name
            }, fields=['role'])
            for row in roles:
                if frappe.get_value("Role", row.role, "desk_access") == 1:
                    active_users += 1
                    break

    if active_users >= allowed_users:
        if not frappe.get_list('User', filters={
            'name': self.name
        }):
            frappe.throw('Only {} active users allowed and you have {} active users. Please disable users or to increase the limit please contact sales'. format(
                allowed_users, len(user_list)))
        elif self.enabled == 1 and active_users > allowed_users:
            frappe.throw('Only {} active users allowed and you have {} active users. Please disable users or to increase the limit please contact sales'. format(
                allowed_users, len(user_list)-1))

    return active_users


def get_directory_size(path):
    '''
    returns total size of directory in MBss
    '''

    output_string = subprocess.check_output(["du", "-mcs", "{}".format(path)])
    total_size = ''
    for char in output_string:
        if chr(char) == "\t":
            break
        else:
            total_size += chr(char)

    return int(total_size)


def update_quota(data):
    """
    To update the values of quota.json for the site
    params: data - dict of keys and values
    fields = [
      'users',
      'active_users',
      'space',
      'db_space',
      'company',
      'used_company',
      'count_website_users',
      'count_administrator_user',
      'valid_till']
    """
    if not isinstance(data, dict):
        frappe.throw(_("'data' must be of type 'dict'"))

    for key in data:
        update_quota_config(key, data[key])
        print("\t{}: {}".format(key, data[key]))
    print(f'Quota updated successfully for {frappe.local.site}')


def update_quota_config(key, value, validate=True, site_config_path=None):
    """Update a value in quota_config"""
    with open(frappe.get_site_path('quota.json'), "r") as f:
        quota = json.loads(f.read())

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
        if key in quota:
            del quota[key]
    else:
        quota[key] = value

    with open(frappe.get_site_path('quota.json'), "w") as f:
        f.write(json.dumps(quota, indent=2, sort_keys=True))


def initialize_quota(site=None):
    """
    Create quota.json file for the current site

    """
    from tint.install import before_install
    before_install(site)


def check_if_quota_exists(site=None):
    """
    To check if site quota.json file is present
    params: site (default is current site)

    """
    if not site:
        site = frappe.local.site
    quota_path = os.path.join(frappe.local.sites_path, site, "quota.json")
    return os.path.exists(quota_path)


def get_quota(site=None):
    """get quota_config"""
    if not site:
        site = frappe.local.site
    quota_path = os.path.join(frappe.local.sites_path, site, "quota.json")
    with open(quota_path, "r") as f:
        quota = json.loads(f.read())
    return quota

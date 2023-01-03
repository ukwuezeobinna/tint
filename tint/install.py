from tint.patches.v1_0.modify_help_dropdown import execute as modify_help_dropdown
from tint.patches.v1_0.remove_report_an_issue_from_help_dropdown import execute as remove_report_an_issue_from_help_dropdown
from tint.patches.v1_0.add_support_option_to_help_dropdown import execute as add_support_option_to_help_dropdown
from tint.tint.central.roles import generate_admin_keys
from tint.tint.doctype.chimso_support_issue.chimso_support_issue import install_default_permissions
import frappe
from frappe.utils.data import today, add_months
import json
import os

from tint.tint.quota import check_if_quota_exists

bench_user = frappe.get_conf().get('frappe_user') or 'chimso'
bench_folder = 'frappe-bench'
bench_path = '/home/{}/{}'.format(bench_user, bench_folder)

def before_install(site=None):
  # if frappe.db.get_default('desktop:home_page') != 'desktop':
  #   print('ERPNext Quota can only be install after setup wizard is completed')
  # Fetching user list
  # skip if quota already exists
  if check_if_quota_exists(site):
    return
  filters = {
    'enabled': 1,
    'name': ['!=','Guest', 'Administrator']
  }
  
  user_list = frappe.get_list('User', filters = filters, fields = ["name"])

  active_users = 0
  
  for user in user_list:
    roles = frappe.get_list("Has Role", filters = {
      'parent': user.name
    }, fields = ['role'])
    for row in roles:
      if frappe.get_value("Role", row.role, "desk_access") == 1: 
        active_users += 1
        break

  data = {
    'users': 5,
    'active_users': active_users,
    'space': 5120,
    'db_space': 100,
    'company': 2,
    'used_company': 1,
    'count_website_users': 0,
    'count_administrator_user': 0,
    'valid_till': add_months(today(), 12)
  }
  # sites_path = frappe.local.sites_path
  # quota_path = frappe.get_site_path('quota.json')
  file_path = bench_path + '/sites/' + \
    frappe.utils.get_site_name(site or frappe.local.site) + \
      '/quota.json'
  print('file path', file_path)
  # if site:
  #   quota_path = os.path.join(file_path, site, 'quota.json')

  with open(file_path, 'w') as outfile:
    json.dump(data, outfile, indent= 2)

  
  print('\nfile quota.json created at ', file_path, 'with the following settings:')
  for key in data: print("\t{}: {}".format(key, data[key]))
  print('\nChange the values in quota.json to change limits\n')

def after_install():
  # add permissions to allow all send chimso support issue
  install_default_permissions()
  generate_admin_keys()
  modify_help_dropdown()
  add_support_option_to_help_dropdown()
  remove_report_an_issue_from_help_dropdown()

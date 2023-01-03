import re
import frappe
from frappe import _
from frappe.utils.data import today, date_diff, get_datetime_str
import json


def successful_login():
    if site_is_exempted():
        print('site bypassed:', frappe.local.site)
        # Bypass checks for special sites
        return
    try:
        with open(frappe.get_site_path('quota.json')) as jsonfile:
            parsed = json.load(jsonfile)
        valid_till = parsed['valid_till']
        diff = date_diff(valid_till, today())
        if diff < 0:
            frappe.throw(
                _("Your site is suspended. Please contact Sales"), frappe.AuthenticationError)
    # TODO: Find a better solution to ensure quota on all sites
    except FileNotFoundError as e:
        print(e)

def site_is_exempted():
    domain = 'chimso.xyz'
    special_subdomains = ['test', 'app', 'main', 'core', 'demo', 'mamtus', 'adai']
    current_site = frappe.local.site
    exempted_sites = [
        f'{subdomain}.{domain}' for subdomain in special_subdomains]
    exempted_sites.append('test.local')
    print('exempted sites', exempted_sites)
    if current_site in exempted_sites or re.search(r'test', current_site, flags=re.IGNORECASE):
        # print('site bypassed:', current_site)
        # Bypass checks for special sites
        return True
    else: return False

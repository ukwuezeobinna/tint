from __future__ import unicode_literals
import frappe
from frappe import _
import re
from requests import request
from tint.tint.central.api import get_payment_settings, get_site_details, update_doc
from tint.events.auth import successful_login
from frappe.utils.password import update_password
from tint.tint.utils import get_query_params
# from frappe.desk.page.setup_wizard.setup_wizard import add_all_roles_to

no_cache = 1


def get_context(context):
    site = frappe.local.site
    url_query = get_query_params(frappe.request.url)
    code = url_query.get('code')
    context.site = site
    central_site = frappe.conf.get('central_api_url')
    msg = 'Please wait a sec...'
    context.msg = msg
    if not code:
        context.access = False
        context.msg = "Access Denied. No access code found"
        return
    # update_password('webuser@test,com', 'test1293??')
    # update_doc('Customer Site', site, {"card_token": "blajdfhowenf", "txref": "hsgfhsdkgrgf","first_log_in": 1})
    # if the site is central, skip
    if re.search(rf'{site}', central_site, flags=re.IGNORECASE):
        context.msg = 'Redirecting to login...'
        context.central = True
        return
    # api_key = frappe.conf.get('admin_auth_key')
    # check if customer site is present
    # print(site, api_key)

    # # context.auth = f'token {api_key}'
    context.msg = 'Checking for site info...'
    site_info = get_site_details(site)
    # payment_settings = get_payment_settings()
    # print(site)
    context.msg = site_info.get('errMsg') if site_info.get('error') else 'Reading Info...'
    if site_info and site_info.get('data'):
        site_info = site_info.get('data')
        access_code = site_info.get('access_code')
        if access_code != code:
            context.access = False
            context.msg = "Access Denied. Site Initialization Failed with wrong access code."
            return
        # print('site info', site_info, site_info.get('first_log_in'))
        context.msg = "Processing..."
        # user has already been welcomed
        if site_info.get('first_log_in') == 1:
            # redirect to desk
            print('Already welcomed, redirecting...')
            msg = "Sorry, this page is not accessible to you"
            context.msg = msg
            context.redirect_to_login = True
            frappe.throw(_("Sorry, this page is not accessible to you"))
        names = site_info.get('customer').split(' ') if site_info.get(
            'customer') else site_info.get('first_user_name').split(' ')
        # check if sub present and status, and card_token/txRef to confirm payment
        # if (site_info.get('card_token') or site_info.get('txref') or site_info.get('promo_code')) or (payment_settings and not payment_settings.payment_required_on_new_site_signup):
            # check create the user and redirect to login
        context.msg = "Creating user..."
        psw = site_info.get('password')
        psw = 'Psw123456!' if psw is None else psw
        email = site_info.get(
            'reg_email') or site_info.get('official_email')
        first_user = frappe.get_doc({
            "doctype": "User",
            "email": email,
            "full_name": site_info.get('customer'),
            "first_name": names[0],
            #"last_name": names[0],
            "enabled": 1,
            "short_bio": "First User and system manager",
            "send_welcome_email": 0,  # consider sending welcome mail
        })
        context.msg = "Saving user..."
        try:
            first_user.insert(ignore_permissions=True)
            context.msg = "User created"
        except frappe.exceptions.DuplicateEntryError:
            # user already exists on the site
            pass
        except:
            context.msg = "Error while creating user"
        update_password(email, psw)
        # add_all_roles_to(first_user.name)
        for role in frappe.db.sql("""select name from tabRole"""):
            if role[0] not in ["Administrator", "Guest", "All", "Customer", "Supplier", "Partner", "Employee"]:
                d = first_user.append("roles")
                d.role = role[0]
        first_user.save(ignore_permissions=True)
        # login as the new user
        frappe.local.login_manager.login_as(email)
        # update the first_log_in param on central and clear the password
        context.msg = 'Updating user info on central'
        update_doc('Customer Site', site, {
                    "first_log_in": 1, "password": ""})

        # redirect user
        context.created = True
        # else:
        #   print('Not permitted. Lacking payment details')
        #   msg = "Not permitted, please complete payment/registration to get access or contact support at support@chimso.xyz"
        #   context.msg = msg
        #   frappe.respond_as_web_page('Not', _(msg), indicator_color='red')
    # No record of the site
    else:
        # redirect
        # print('No record found')
        context.access = False
        context.msg = "No record Found"
        # context.redirect_to_login = True
    # pass

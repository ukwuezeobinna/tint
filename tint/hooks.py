# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from . import __version__ as app_version

app_name = "tint"
app_title = "Tint"
app_publisher = "Chimso XYZ"
app_description = "Chimso Customization App"
app_icon = "octicon octicon-file-directory"
app_color = "grey"
app_email = "matthew@chimso.xyz"
app_license = "MIT"
source_link = "git@bitbucket.org:mh-chimso/tint.git"
app_logo_url = '/assets/tint/images/chimso_icon.png'

website_context = {
	"favicon": 	"/assets/tint/images/chimso_icon.png",
	"splash_image": "/assets/tint/images/chimso_icon.png"
}

# Overriding Methods
# ------------------------------
#
override_whitelisted_methods = {
	"erpnext.setup.utils.get_exchange_rate": "tint.tint.setup.utils.get_exchange_rate"
}

# scheduler_events = {
#     "hourly": [
#         # will run hourly
#         "app.scheduled_tasks.update_database_usage"
#     ],
# }

# Default Mail Settings
# ------------------------------
# 
email_brand_image = "assets/tint/images/chimso_icon.png"

default_mail_footer = """
    <div>
        Sent via <a href="https://www.chimso.xyz" target="_blank">Chimso XYZ</a>
    </div>
"""

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/tint/css/tint.css"
app_include_js = "/assets/tint/js/tint.js"

# include js, css files in header of web template
# web_include_css = "/assets/tint/css/tint.css"
web_include_js = "/assets/tint/js/tint.js"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
    "Sales Invoice" : "public/js/custom/sales_invoice.js",
    "Quotation": "public/js/custom/quotation.js",
    "Delivery Note": "public/js/custom/delivery_note.js",
    "Sales Order": "public/js/custom/sales_order.js"
}
doctype_list_js = {"User" : "public/js/user_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Installation
# ------------

before_install = "tint.install.before_install"
after_install = "tint.install.after_install"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "tint.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
#	}
# }

on_login = 'tint.events.auth.successful_login'

doc_events = {
    'User': {
        'validate': 'tint.tint.quota.user_limit',
        'on_update': 'tint.tint.quota.user_limit'
    },
    'Company': {
        'validate': 'tint.tint.quota.company_limit',
        'on_update': 'tint.tint.quota.company_limit'
    },
    '*': {
        'on_submit': 'tint.tint.quota.db_space_limit'
    },
    'File': {
        'validate': 'tint.tint.quota.files_space_limit'
    },
    'Comment': {
        'after_insert': 'tint.tint.doctype.chimso_support_issue.chimso_support_issue.sync_with_chimso'
    }
}

# Scheduled Tasks
# ---------------

scheduler_events = {
	"daily": [
		"tint.tasks.daily"
	],
	"hourly": [
		"tint.chimso_pay.doctype.payment_details.payment_details.update_payment_details",
    "tint.chimso_pay.doctype.salary_payout.salary_payout.update_all_payouts",
    "tint.accounting_addon.doctype.price_adjustment.price_adjustment.check_incomplete_adjustments"
	],
}
# scheduler_events = {
# 	"all": [
# 		"tint.tasks.all"
# 	],
# 	"daily": [
# 		"tint.tasks.daily"
# 	],
# 	"weekly": [
# 		"tint.tasks.weekly"
# 	]
# 	"monthly": [
# 		"tint.tasks.monthly"
# 	]
# }

# Testing
# -------

# before_tests = "tint.install.before_tests"

# Overriding Methods
# ------------------------------
#
override_whitelisted_methods = {
	"frappe.core.doctype.user.user.generate_keys": "tint.tint.central.roles.generate_keys",
}
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "tint.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]


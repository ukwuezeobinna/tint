# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from frappe import _

def get_data():
	return [
		{
			"module_name": "Accounts",
			"category": "Modules",
			"label": _("Accounting"),
			"color": "#3498db",
			"icon": "fa fa-tint",
			"type": "module",
			"description": "Accounts, billing, payments, cost center and budgeting."
		},
		{
			"module_name": "Tint",
			"color": "grey",
			"icon": "fa fa-tint-icon",
			"icon_url": "/assets/tint/images/fa-tint.svg",
			"app_icon_url": "/assets/tint/images/fa-tint.svg",
			"type": "module",
			"label": _("Tint")
		}
	]

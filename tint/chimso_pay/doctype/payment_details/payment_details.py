# -*- coding: utf-8 -*-
# Copyright (c) 2021, Chimso XYZ and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import re
from tint.tint.central.api import trigger_method
import frappe
# import frappe
from frappe.model.document import Document

class PaymentDetails(Document):
	pass

@frappe.whitelist()
def update_payment_details():
	payment_details_list = frappe.get_all("Payment Details")
	frappe.msgprint("Update of payment details started...")
	for pd in payment_details_list:
		check_status_and_update(pd.name)

@frappe.whitelist()
def check_status_and_update(docname):
	# call flutterwave get_tranfer to check status 
	# if transaction_id
	if frappe.db.exists("Payment Details", docname):
		trx_id = frappe.db.get_value("Payment Details", docname, "transaction_id")
		status = frappe.db.get_value("Payment Details", docname, "status")
		print("trx id", trx_id, status)
		completed_statuses = ["SUCCESSFUL"] # removed failed status incase of retries
		regex = re.search(r'successful', status, re.IGNORECASE)
		if status in completed_statuses or regex: return
		
		if trx_id:
			method_path = "central.central.doctype.flutterwave_settings.flutterwave_settings.fetch_transfer"
			data = {
				"transaction_id": trx_id
			}
			res = trigger_method(method_path=method_path, data=data).get("message")
			print("Transfer fetched", res)
			if res and res.get("status") and res.get("data"):
				trx_data = res.get("data")
				frappe.db.set_value("Payment Details", docname, "status", trx_data.get("status"))
				full_msg = "{flw_msg}. Transfer of {cur} {amt} to {fullname} (fee: {fee}): {status}".format(
					flw_msg=trx_data.get("complete_message"), cur=trx_data.get("currency"), amt=trx_data.get("amount"), fee=trx_data.get("fee"), fullname=trx_data.get("full_name"), status=trx_data.get("status"))
				frappe.db.set_value("Payment Details", docname, "response", full_msg)
				frappe.db.set_value("Payment Details", docname, "txref", trx_data.get("reference"))


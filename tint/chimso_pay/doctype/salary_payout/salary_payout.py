# -*- coding: utf-8 -*-
# Copyright (c) 2021, Chimso XYZ and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import re
from requests.sessions import session
from six import b
from ....chimso_pay import charge_card, get_balance, get_bank_list, init_transfer, validate_card_charge, make_transfer_claim
import frappe
from frappe.model.document import Document
from frappe.utils import random_string


class SalaryPayout(Document):
	def before_save(self):
		# calculate the estimated total
		total = 0
		for detail in self.salary_slips:
				print(detail.salary_slip)
				net_total = frappe.db.get_value(
						"Salary Slip", detail.salary_slip, "base_net_pay")
				total += net_total
		self.total_amount = total
		print(self.total_amount)
	
	def make_payout(self):
		# TODO: add more validation
		if self.deposit_amount > self.total_amount:
			slips = self.salary_slips
			bank_list = get_bank_list().get("message")
			print("bank list", bank_list)
			for slip in slips:
				if slip.transfer_details:
					print(slip.name, "transfer already started... Update and skip")
					continue
				print(slip.name)
				amount = frappe.db.get_value("Salary Slip", slip.salary_slip, "base_net_pay")
				paymentDetail = frappe.get_doc({
					"doctype": "Payment Details",
					"status": "Initiated",
					"amount": amount,
					"beneficiary": frappe.db.get_value("Salary Slip", slip.salary_slip, "employee_name"),
					"reference_document": slip.salary_slip,
					"payment_type": "Transfer",
					"salary_payout": self.name
				})
				paymentDetail.insert(ignore_permissions=True, ignore_mandatory=True)
				frappe.db.set_value("Payout Receiver Details", slip.name, "transfer_details", paymentDetail.name)
				# check balance
				res = get_balance().get("message")
				print("balance", res)
				if res.get("data"):
					bal = res.get("data")["available_balance"]
					if bal < amount:
						paymentDetail.error = "Insufficient Balance"
						paymentDetail.response = "{}".format(res)
						paymentDetail.status = "Failed"
						paymentDetail.save(ignore_permissions=True)
					else:
						# get bank code
						print("slip row", slip.as_dict(), slip.bank_name)
						bank_code = next((i.get("code") for i in bank_list["data"] if i["name"].lower() == slip.bank_name.lower()), None)
						print("bank code", bank_code)
						if bank_code:
							# init transfer
							transferData = {
								"account_bank": bank_code,
								"account_number": slip.bank_account,
								"amount": amount,
								"Narration": "Employee Salary",
								"currency": frappe.defaults.get_user_default("currency") or "NGN",
								"beneficiary_name": frappe.db.get_value("User", frappe.session.user, "full_name")
								# TODO: add reference
							}
							resp  = init_transfer(paymentDetails=transferData)
							print(resp)
							if resp.get("message"):
								if (resp.get("message").get("id")):
									paymentDetail.transaction_id = resp.get("message").get("id")
									paymentDetail.response = "Pending Approval"
									paymentDetail.save(ignore_permissions=True)

						else:
							paymentDetail.error = "Bank Code for {} not found".format(slip.bank_name)
							paymentDetail.response = bal
							paymentDetail.status = "Failed"
							paymentDetail.save(ignore_permissions=True)
				
			frappe.db.set_value("Salary Payout", self.name, "transfer_queued", 1)
			# self.save()
			return {"message": "Transfers added to queue"}

	def update_status(self):
		state = {
			"successful": 0,
			"failed": 0,
			"pending": 0
		}
		print("Update started")
		for row in self.salary_slips:
			if row.transfer_details:
				status = frappe.db.get_value("Payment Details", row.transfer_details, "status")
				print(row.name, row.transfer_details, status)
				if re.search(r'successful', status, re.IGNORECASE):
					status = "Paid"
					print("plus 1 for successful")
					state["successful"] += 1
				elif re.search(r'failed', status, re.IGNORECASE):
					status = "Failed"
					state["failed"] += 1
				elif re.search(r'init', status, re.IGNORECASE):
					status = "Pending"
					state["pending"] += 1
				else:
					state["pending"] += 1
					status = "Pending"
				print("status before setting", status)
				frappe.db.set_value("Payout Receiver Details", row.name, "status", status)
		
		# TODO: also update the transfer complete status
		if state.get("failed") == 0 and state.get("pending") == 0:
			frappe.db.set_value("Salary Payout", self.name, "transfer_queued", 0)
			frappe.db.set_value("Salary Payout", self.name, "transfer_status", "Successful")
		print(state)
		return state

	def retry_failed_payouts(self):
		pass


@frappe.whitelist()
def initialize_payment(card_number, card_cvc, month, year, amount, docname, suggestedAuth=None, pin=None, address=None, country=None, currency=None):
	user = frappe.session.user
	fullname = frappe.db.get_value("User", user, "full_name")
	name_arr = fullname.split(' ')
	email = frappe.db.get_value("User", user, "email")
	country = country or frappe.defaults.get_user_default("country")
	country_code = frappe.db.get_value("Country", country, "code")
	phonenumber = frappe.db.get_value("User", user, "mobile_no")
	txRef = 'Chimso-pay-{}-{}'.format(docname, random_string(4))
	frappe.db.set_value("Salary Payout", docname, "txRef", txRef)
	frappe.db.set_value("Salary Payout", docname, "deposit_amount", amount)
	data = {
		"cardno": card_number,
		"cvv": card_cvc,
		"expirymonth": month,
		"expiryyear": year,
		"currency": currency or frappe.defaults.get_user_default("currency"),
		"country": country_code,
		"firstname": frappe.local.site.split(".")[0] if len(name_arr) == 1 else name_arr[1],
		"lastname": name_arr[0],
		"email": email,
		"IP": "18.208.204.35", # server ip as default
		"phonenumber": phonenumber,
		"payment_options": "card",
		"txRef": txRef,
		"amount": amount,
		"meta": {
			"consumer_id": email
		},
		"customer": {
			"email": email,
			"phonenumber": phonenumber,
			"name": fullname
		}
	}
	return charge_card(data=data, suggestedAuth=suggestedAuth, pin=pin, address=address).get("message")

@frappe.whitelist()
def validate_payment(flwRef, otp, docname):
	paymentDetail = frappe.get_doc({
		"doctype": "Payment Details",
		"status": "Pending",
		"amount": frappe.db.get_value("Salary Payout", docname, "deposit_amount"),
		"response": "{}".format(flwRef),
		"flwref": flwRef,
		"reference_document": docname,
		"payment_type": "Card",
		"salary_payout": docname,
		"txref": frappe.db.get_value("Salary Payout", docname, "txref")
	})
	paymentDetail.insert(ignore_permissions=True)
	print('payD doc', paymentDetail.as_dict())
	frappe.db.set_value("Salary Payout", docname, "flwRef", flwRef)
	frappe.db.set_value("Salary Payout", docname, "deposit_document", paymentDetail.name)
	res = validate_card_charge(flwRef=flwRef, otp=otp).get("message")
	if res.get("status") == "success":
		frappe.db.set_value("Salary Payout", docname, "verified_payment", 1)
		frappe.db.set_value("Salary Payout", docname, "awaiting_confirmation", 0)
	return res

@frappe.whitelist()
def make_payout(payout_docname):
	doc = frappe.get_doc("Salary Payout", payout_docname)
	return doc.make_payout()


@frappe.whitelist()
def transfer_claim(amount, docname):
  print("amount", amount)
  paymentDetail = frappe.get_doc({
			"doctype": "Payment Details",
			"status": "Initiated",
			"amount": amount,
			"reference_document": docname,
			"payment_type": "Transfer",
			"salary_payout": docname
	})
  paymentDetail.insert(ignore_permissions=True, ignore_mandatory=True)

  claim = {
		"amount": amount,
		"site": frappe.local.site,
		"name": frappe.db.get_value("User", frappe.session.user, "full_name"),
		"docname": docname,
		"payment_doc": paymentDetail.name
  }
	# TODO: add payment details and send with claim
  frappe.db.set_value("Salary Payout",docname, "deposit_amount", amount)
  frappe.db.set_value("Salary Payout",docname, "awaiting_confirmation", 1)
  frappe.db.set_value("Salary Payout",docname, "verified_payment", 0)
  return make_transfer_claim(claim).get("message")

@frappe.whitelist()
def confirm_transfer(docname, payment_doc):
  frappe.db.set_value("Salary Payout", docname, "awaiting_confirmation", 0)
  frappe.db.set_value("Salary Payout", docname, "verified_payment", 1)
  paymentDetail = frappe.get_doc("Payment Details", payment_doc)
  paymentDetail.response = "Transfer confirmed and payout triggered"
  paymentDetail.status = "Confirmed"
  paymentDetail.save()
	# trigger payout
  payout = frappe.get_doc("Salary Payout", docname)
  payout.make_payout()
  return {"success": True, "msg": "Transfer claim confirmed and payout triggered"}


@frappe.whitelist()
def update_payout_status(docname):
	doc = frappe.get_doc("Salary Payout", docname)
	frappe.msgprint(frappe._("Update in progress..."))
	doc.update_status()

@frappe.whitelist()
def update_all_payouts():
	payout_list = frappe.get_all("Salary Payout")
	for payout in payout_list:
		update_payout_status(payout.name)

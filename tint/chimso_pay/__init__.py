import frappe
from tint.tint.central.api import trigger_method

@frappe.whitelist()
def get_payment_fee(currency=None, amount=0):
  print(frappe.defaults.get_user_default("currency"), currency)
  method_path = "central.central.doctype.flutterwave_settings.flutterwave_settings.get_transfer_fee"
  data = {
    "currency": currency or frappe.defaults.get_user_default("currency"),
    "amount": amount
  }
  return trigger_method(method_path, data)

@frappe.whitelist()
def get_balance(currency="NGN"):
  print(frappe.defaults.get_user_default("currency"), currency)
  method_path = "central.central.doctype.flutterwave_settings.flutterwave_settings.get_balance"
  data = {
    "currency": currency or frappe.defaults.get_user_default("currency"),
  }
  return trigger_method(method_path, data)

@frappe.whitelist()
def get_bank_list(country="NG"):
  method_path = "central.central.doctype.flutterwave_settings.flutterwave_settings.get_bank_list"
  data = {
    "country": country or frappe.defaults.get_user_default("country"),
  }
  return trigger_method(method_path, data)

@frappe.whitelist()
def get_topup_account():
  method_path = "central.central.doctype.flutterwave_settings.flutterwave_settings.get_topup_account"
  return trigger_method(method_path)

@frappe.whitelist()
def retry_transfer(transaction_id):
  method_path = "central.central.doctype.flutterwave_settings.flutterwave_settings.retry_transfer"
  data = {
    "transaction_id": transaction_id,
  }
  return trigger_method(method_path, data)

@frappe.whitelist()
def init_transfer(paymentDetails):
  """
  paymentDetails is a dictionary of transfer details
  """
  method_path = "central.central.doctype.flutterwave_settings.flutterwave_settings.init_transfer"
  data = {
    "paymentDetails": paymentDetails,
  }
  return trigger_method(method_path, data)

@frappe.whitelist()
def charge_card(data, suggestedAuth=None, pin=None, address=None):
  """
  data is a dictionary of transfer details
  """
  method_path = "central.central.doctype.flutterwave_settings.flutterwave_settings.charge_card"
  args = {
    "data": data,
    "suggestedAuth": suggestedAuth,
    "pin": pin,
    "address": address
  }
  return trigger_method(method_path, data=args)

@frappe.whitelist()
def validate_card_charge(flwRef, otp):
  method_path = "central.central.doctype.flutterwave_settings.flutterwave_settings.validate_card_charge"
  args = {
    "flwRef": flwRef,
    "otp": otp
  }
  return trigger_method(method_path, data=args)

@frappe.whitelist()
def verify_charge(txRef):
  method_path = "central.central.doctype.flutterwave_settings.flutterwave_settings.verify_card_charge"
  args = {
    "txRef": txRef
  }
  return trigger_method(method_path, data=args)

@frappe.whitelist()
def make_transfer_claim(args):
  method_path = "central.api.make_transfer_claim"
  
  return trigger_method(method_path, data=args)

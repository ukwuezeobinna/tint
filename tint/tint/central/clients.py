from central.api.api import trigger_method
import frappe
from frappe import _
from tint.tint.central.api import trigger_method

"""
Handles most requests from central via api not already done by frappe.client
"""

@frappe.whitelist()
def check_if_doc_exists(doctype, name, filters={}, fields=[]):
  """
  Checks if dt exists
  """
  return frappe.db.exists(doctype, name, filters=filters, fields=[])


@frappe.whitelist(allow_guest=True)
def verify_access_request(user, access_key, role):
  """
  Calls central via api to verify access request is valid
  """
  central_api_url = frappe.conf.get("central_api_url")
  admin_auth_key = frappe.conf.get("admin_auth_key")
  if not central_api_url or not admin_auth_key:
    frappe.throw(_("Not permitted, no api access or url to central found. Please initialize or contact support"))
  method_path = "central.api.verify_access_request"
  data = {
    "user": user,
    "access_key": access_key,
    "role": role
  }
  response = trigger_method(method_path=method_path, data=data)
  print('verification response', isinstance(response, str), response)
  return response.get('message') if response.get('message') else response

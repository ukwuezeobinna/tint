import frappe
from frappe import _
from tint.tint.central.utils import generate_api_url_and_header
import requests

"""
Handles api access from tint to central

"""

@frappe.whitelist(allow_guest=True)
def get_site_details(site):
  try:
    # url, header = generate_api_url_and_header(f'/resource/Customer Site/{site}')
    # response = requests.get(url=url, headers=header)
    data = {'doctype': 'Customer Site', 'docname': site}
    method_path = 'central.api.get_doc'
    return trigger_method(data=data, method_path=method_path).get('message')
    # if response.status_code == 200:
    #   return response.json()
    # else: return {'site': site, 'status_code': response.status_code, 'error': response.json(), 'header': header}
  except Exception as e:
    return {'success': False, 'errMsg': e, 'error': True}

@frappe.whitelist(allow_guest=True)
def get_payment_settings():
  url, header = generate_api_url_and_header(f'/resource/Payment Settings/Payment Settings')
  response = requests.get(url=url, headers=header)
  response.raise_for_status()
  if response.status_code == 200:
    return response.json()
  else: return {}


def update_doc(doctype, name, data):
  if not data: 
    frappe.throw(_("'data' can not be empty and must be a type of 'dict'"))
  # print('attempting to update', data.keys())
  url, header = generate_api_url_and_header(f'/resource/{doctype}/{name}')
  response = requests.put(url=url, json=data, headers=header)
  response.raise_for_status()
  # print(response.status_code, url)
  if response.status_code == 200:
    return response.json()
  else: return {}

def insert_doc(doctype, data):
  url, header = generate_api_url_and_header(f'/resource/{doctype}')
  response = requests.post(url=url, json=data, headers=header)
  print('Response from insert_doc to central', response.status_code, response.json())
  response.raise_for_status()
  if response.status_code == 200:
    return response.json()
  else: return {}


def get_doc(doctype, name, filters=[], fields=[]):
  url, header = generate_api_url_and_header(f'/resource/{doctype}/{name}?filters={filters}&fields={fields}')
  response = requests.get(url=url, headers=header)
  print(response.status_code)
  response.raise_for_status()
  if response.status_code == 200:
    return response.json()
  else: return {}


@frappe.whitelist()
def trigger_method(method_path, data=None, base_url=None):
  """
  To call a method on a site via api on central
  """
  # print('attempting to update', data.keys())
  url, header = generate_api_url_and_header(f'/method/{method_path}', base_url=base_url)
  response = requests.post(url=url, json=data, headers=header)
  # print(response.status_code, url)
  response.raise_for_status()
  if response.status_code == 200:
    return response.json()
  else:
    return {}

# def validate_response(res):

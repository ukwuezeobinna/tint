from __future__ import unicode_literals
import json
import re
from urllib import parse
from re import IGNORECASE
import frappe
from frappe import _
from subprocess import Popen, PIPE, STDOUT
import shlex
import os
import json

from frappe.utils import random_string
# from frappe.core.doctype.user.user import generate_keys

"""
General functions used by central module

"""


def run_command(commands, doctype, key, cwd='..', docname=' ', after_command=None):
	# verify_whitelisted_call()
	start_time = frappe.utils.time.time()
	console_dump = ""
	logged_command = " && ".join(commands)
	logged_command += " "  # to make sure passwords at the end of the commands are also hidden
	sensitive_data = ["--mariadb-root-password",
                   "--admin-password", "--root-password"]
	for password in sensitive_data:
		logged_command = re.sub(
		    "{password} .*? ".format(password=password), '', logged_command, flags=re.DOTALL)
	frappe.db.commit()
	frappe.publish_realtime(key, "Executing Command:\n{logged_command}\n\n".format(
	    logged_command=logged_command), user=frappe.session.user)
	try:
		for command in commands:
			terminal = Popen(shlex.split(command), stdin=PIPE,
			                 stdout=PIPE, stderr=STDOUT, cwd=cwd)
			for c in iter(lambda: safe_decode(terminal.stdout.read(1)), ''):
				frappe.publish_realtime(key, c, user=frappe.session.user)
				console_dump += c
		if terminal.wait():
			_close_the_doc(start_time, key, console_dump,
			               status='Failed', user=frappe.session.user)
		else:
			_close_the_doc(start_time, key, console_dump,
			               status='Success', user=frappe.session.user)
	except Exception as e:
		_close_the_doc(start_time, key, "{} \n\n{}".format(
		    e, console_dump), status='Failed', user=frappe.session.user)
	finally:
		frappe.db.commit()
		# hack: frappe.db.commit() to make sure the log created is robust,
		# and the _refresh throws an error if the doc is deleted
		frappe.enqueue('tint.tint.central.utils._refresh',
                 doctype=doctype, docname=docname, commands=commands)


def _refresh(doctype, docname, commands):
	frappe.get_doc(doctype, docname).run_method(
	    'after_command', commands=commands)

def _close_the_doc(start_time, key, console_dump, status, user):
	time_taken = frappe.utils.time.time() - start_time
	final_console_dump = ''
	console_dump = console_dump.split('\n\r')
	for i in console_dump:
		i = i.split('\r')
		final_console_dump += '\n'+i[-1]
	frappe.publish_realtime(
	    key, '\n\n'+status+'!\nThe operation took '+str(time_taken)+' seconds', user=user)


def safe_decode(string, encoding='utf-8'):
	try:
		string = string.decode(encoding)
	except Exception:
		pass
	return string

def generate_api_url_and_header(endpoint, base_url=None):
  default_url = frappe.conf.get('central_api_url', '')
  if base_url is None:
    base_url = default_url
  env = frappe.conf.get('env')
  import re
  # print('base_url', base_url, re.search(r'http', base_url, flags=IGNORECASE))
  if isinstance(endpoint, str) == False:
    return {"error": 'Invalid endpoint. Endpoint must be a string'}
  if not base_url:
    frappe.throw(_("Api url can not be None, please provide url or set default in config"))
  http = ''
  port = ':{}'.format(frappe.conf.get("webserver_port")
                      ) if (frappe.conf.get('env') and (not bool(re.search(r'\:\d', base_url, flags=IGNORECASE)))) else ''
                    #   ) if (frappe.conf.get('env') and (not re.search(r'\:\d', base_url, flags=IGNORECASE))) == 'dev' else ''
  # print(re.search(r'\:\d', base_url, flags=IGNORECASE), 'port', port)
  if not re.search(r'http', base_url, flags=IGNORECASE): http='https://' if env != 'dev' else 'http://'
  url = '{http}{base_url}{port}/api{endpoint}'.format(http=http, base_url=base_url, endpoint=endpoint, port=port)
  key = frappe.conf.get('admin_auth_key')
  auth = "token {}".format(key)
  header = {"Authorization": auth}
#   print('url', url, bool(re.search(r'\:\d', base_url, flags=IGNORECASE)), header)
  return url, header

@frappe.whitelist()
def get_site_config(site=None):
  """get site_config"""
  if not site:
    site = frappe.local.site
  site_path = os.path.join(frappe.local.sites_path, site, "site_config.json")
  with open(site_path, "r") as f:
    config = json.loads(f.read())
  return config


@frappe.whitelist()
def get_query_params(url):
  return dict(parse.parse_qsl(parse.urlsplit(url).query))


@frappe.whitelist()
def disable_site(key=random_string(12)):
  site_name = frappe.local.site
  commands = ["bench --site {} set-maintenance-mode on".format(site_name)]

  frappe.enqueue('tint.tint.central.utils.run_command',
                commands=commands,
                doctype="Usage Info",
                key=key
                )
@frappe.whitelist()
def enable_site(key=random_string(12)):
  site_name = frappe.local.site
  commands = ["bench --site {} set-maintenance-mode off".format(site_name)]
  print('enabling site')
  frappe.enqueue('tint.tint.central.utils.run_command',
                commands=commands,
                doctype="Usage Info",
                key=key
                )

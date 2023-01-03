from __future__ import unicode_literals
import frappe
from frappe import _, msgprint
from frappe.utils import flt, add_days
from frappe.utils import get_datetime_str, nowdate
from erpnext import get_default_company
import requests

@frappe.whitelist()
def get_exchange_rate_with_flutterwave(from_currency, to_currency, amount=1):
	# frappe.msgprint(_("Inside flw fn"))
	api_key = "FLWSECK-680d2bcff3fb5db014ffbff31b351363-X"
	# frappe.msgprint(_("1.1"))
	auth = "Bearer {}".format(api_key)
	header = {"Authorization": auth}
	# frappe.msgprint(_("1.2"))
	api_url = "https://api.flutterwave.com/v3/rates"
	# frappe.msgprint(_(f'amount to convert {amount} {isinstance(amount, int)}'))
	response = requests.get(api_url, params={
            "amount": amount,
            "from": from_currency,
            "to": to_currency
        }, headers=header)
	# frappe.msgprint(_("1.3"))
	response.raise_for_status()
	# frappe.msgprint(_("1.4"))
	# frappe.msgprint(_(response.status_code))#, response.json()['data']['to']['amount']))
	value = response.json()["data"]['to']['amount']
	# frappe.msgprint(_(f"1.5 {response.json()}"))
	return value

@frappe.whitelist()
def get_exchange_rate(from_currency, to_currency, transaction_date=None, args=None):
	# frappe.msgprint(_(f"Starting currency conversion {from_currency} {to_currency}"))
	frankfurter_currencies = {}
	if not (from_currency and to_currency):
		# manqala 19/09/2016: Should this be an empty return or should it throw an exception?
		return
	if from_currency == to_currency:
		return 1

	if not transaction_date:
		transaction_date = nowdate()
	currency_settings = frappe.get_doc("Accounts Settings").as_dict()
	allow_stale_rates = currency_settings.get("allow_stale")

	filters = [
		["date", "<=", get_datetime_str(transaction_date)],
		["from_currency", "=", from_currency],
		["to_currency", "=", to_currency]
	]

	if args == "for_buying":
		filters.append(["for_buying", "=", "1"])
	elif args == "for_selling":
		filters.append(["for_selling", "=", "1"])

	if not allow_stale_rates:
		stale_days = currency_settings.get("stale_days")
		checkpoint_date = add_days(transaction_date, -stale_days)
		filters.append(["date", ">", get_datetime_str(checkpoint_date)])

	# cksgb 19/09/2016: get last entry in Currency Exchange with from_currency and to_currency.
	entries = frappe.get_all(
		"Currency Exchange", fields=["exchange_rate"], filters=filters, order_by="date desc",
		limit=1)
	if entries:
		return flt(entries[0].exchange_rate)

	try:
		cache = frappe.cache()
		# frappe.msgprint(_("3.5"))
		key = "currency_exchange_rate_{0}:{1}:{2}".format(
			transaction_date, from_currency, to_currency)
		value = cache.get(key)
		# print('value cache', value)
		# print('cached', cache.get("test"))

		if not value:
			api_currency_url = "https://api.frankfurter.app/currencies"
			# frappe.msgprint(_("2"))
			response = requests.get(api_currency_url)
			response.raise_for_status()
			# frappe.msgprint(_("3.4"))
			frankfurter_currencies = response.json()
			# if not, raise exception and try flutterwave
			if frankfurter_currencies.get(from_currency) is None or frankfurter_currencies.get(to_currency) is None:
				# frappe.msgprint(_(f'here rn {frankfurter_currencies.get(to_currency)}'))
				print('raising exception')
				raise Exception
			api_url = "https://frankfurter.app/{0}".format(transaction_date)
			response = requests.get(api_url, params={
				"base": from_currency,
				"symbols": to_currency
			})
			# frappe.msgprint(_(response.status_code))
			# expire in 6 hours
			response.raise_for_status()
			value = response.json()["rates"][to_currency]
			# frappe.msgprint(_('value from frankfurter', value))
			cache.set(key, value, ex=6 * 60 * 60)
			# frappe.msgprint(_('after cache'))
		# frappe.msgprint(_('before return'))
		return flt(value)
	except:
		try:
			# frappe.msgprint(_('using flutterwave'))
			value = get_exchange_rate_with_flutterwave(from_currency=from_currency, to_currency=to_currency)
			# frappe.msgprint(_(value))
			# frappe.msgprint(_("3.52"))
			cache = frappe.cache()
			key = "currency_exchange_rate_{0}:{1}:{2}".format(transaction_date, from_currency, to_currency)
			# frappe.msgprint(_('value before cache', value))
			# adding try to outofrange exceptions etc
			# cache.set('test', 10, ex=6 * 60 * 60)
			cache.set(key, value, ex=6 * 60 * 60)
			print('cached', cache.get(key))
			return flt(value)
		except:
			# frappe.msgprint(_(f'trying both {frankfurter_currencies.get(from_currency)} {frankfurter_currencies.get(to_currency)}'))
			# if the first currency is available in frankfurter
			if frankfurter_currencies.get(from_currency) is not None:
				# convert to usd with frankfurter
				# frappe.msgprint(_("4"))
				try:
					api_url = "https://frankfurter.app/{0}".format(transaction_date)
					# frappe.msgprint(_("5"))
					response = requests.get(api_url, params={
						"base": from_currency,
						"symbols": 'USD'
					})
					# frappe.msgprint(_("6"))
					# frappe.msgprint(_(response.json(), response.status_code))
					# expire in 6 hours
					response.raise_for_status()
					usd_value = response.json()["rates"]['USD']
					# frappe.msgprint(_('USD value for {} is {}'.format(from_currency, usd_value)))
					# then try converting with flw
					value = get_exchange_rate_with_flutterwave(from_currency='USD', to_currency=to_currency, amount=usd_value)
					cache = frappe.cache()
					key = "currency_exchange_rate_{0}:{1}:{2}".format(transaction_date, from_currency, to_currency)
					cache.set(key, value, ex=6 * 60 * 60)
					# frappe.msgprint(_('value', value))
					return flt(value)
				except:
					frappe.log_error(title="Get Exchange Rate")
					frappe.msgprint(_("Unable to find exchange rate for {0} to {1} for key date {2}. Please create a Currency Exchange record manually").format(
						from_currency, to_currency, transaction_date))
					return 0.0
			else:
				frappe.log_error(title="Get Exchange Rate")
				frappe.msgprint(_("Unable to find exchange rate for {0} to {1} for key date {2}. Please create a Currency Exchange record manually").format(
                                    from_currency, to_currency, transaction_date))
				return 0.0

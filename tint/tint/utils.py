from urllib import parse
from frappe.email.doctype.notification.notification import get_context
import json
import sys
import frappe
from frappe import _
from frappe.utils import get_request_session
from frappe.desk.doctype.notification_log.notification_log import enqueue_create_notification


def send_get_request(url, headers=None, params=None, raise_for_status=1):
    """To send a get request to central site"""

    try:
        s = get_request_session()
        res = s.get(
            url=url, params=params, headers=headers)
        print('sent get request', res.status_code)
        if raise_for_status:
            res.raise_for_status()
        return res.json()
    except Exception as exc:
        frappe.log_error()
        raise exc


def send_put_request(url, headers=None, json={}, data={}):
    try:
        s = get_request_session()
        res = s.put(
            url=url, json=json, data=data, headers=headers)
        # res.raise_for_status()
        print('sent put request', res.status_code)

        return res.json()
    except Exception as exc:
        frappe.log_error()
        raise exc


def send_post_request(url, headers=None, json={}, data={}):
    try:
        s = get_request_session()
        res = s.post(
            url=url, json=json, data=data, headers=headers)
        print('sent post request', res.status_code)
        return res.json()
    except Exception as exc:
        frappe.log_error()
        raise exc


def update_on_proxy_server(url, data):
    send_put_request(url=url, json=data)


def post_to_proxy_server(url, data):
    send_put_request(url=url, json=data)


def update_key_on_proxy(key, site=None):
    # get site
    wb_url = frappe.conf.get('webhook_url')
    site = site or frappe.local.site
    site_url = site + ':{}'.format(frappe.conf.get("webserver_port")
                                   ) if frappe.conf.get('env') == 'dev' else ''
    if not wb_url:
        frappe.throw(_("Webhook Server not set. Please do that and try again"))
    else:
        url = wb_url + '/sites/{}'.format(site_url)
        res = send_get_request(url, raise_for_status=0)
    # if site, update
        if res and res.get('site_name'):
            url = wb_url + '/sites/{}'.format(res.get('id'))
            data = {"api_key": key}
            resp = send_put_request(url=url, json=data)
            if resp and resp.get('site_name'):
                print('key updated for', site)
                return resp
            else:
                print('error occurred during update', resp)
    # else create
        elif res and res.get('status') == 404:
            url = wb_url + '/sites'
            data = {"site_name": site_url, "api_key": key}
            resp = send_post_request(url=url, json=data)
            if resp and resp.get('site_name'):
                print('key updated for', site)
                return resp
            else:
                print('error occurred during update', resp)


@frappe.whitelist()
def create_system_notification(doc, users, message, subject, attach_print=None):
    context = get_context(doc)
    if "{" in subject:
        subject = frappe.render_template(subject, context)

    if attach_print:
        attachments = get_attachment(doc)

    notification_doc = {
        'type': 'Alert',
        'document_type': doc.doctype,
        'document_name': doc.name,
        'subject': subject,
        'from_user': doc.modified_by or doc.owner,
        'email_content': frappe.render_template(message, context),
        # 'attached_file': attachments and json.dumps(attachments[0])
    }
    enqueue_create_notification(users, notification_doc)


def get_attachment(doc, print_format=None):
    """ check print settings are attach the pdf """
    print_settings = frappe.get_doc("Print Settings", "Print Settings")
    if (doc.docstatus == 0 and not print_settings.allow_print_for_draft) or \
            (doc.docstatus == 2 and not print_settings.allow_print_for_cancelled):

        # ignoring attachment as draft and cancelled documents are not allowed to print
        status = "Draft" if doc.docstatus == 0 else "Cancelled"
        frappe.throw(_("""Not allowed to attach {0} document, please enable Allow Print For {0} in Print Settings""").format(status),
                     title=_("Error in Notification"))
    else:
        return [{
                "print_format_attachment": 1,
                "doctype": doc.doctype,
                "name": doc.name,
                "print_format": print_format,
                "print_letterhead": print_settings.with_letterhead,
                "lang": frappe.db.get_value('Print Format', print_format, 'default_print_language')
                if print_format else 'en'
                }]


def progress(count, total, status=""):
    """
    create and update terminal progress bar
    @param count|int or float|: current progress
    @param total|int or float|: maximum limit of progress
    @param status|str|: message to update
    """
    bar_len = 60
    filled_len = int(round(bar_len * count / float(total)))

    percents = round(100.0 * count / float(total), 1)
    bar = '=' * filled_len + '-' * (bar_len - filled_len)

    sys.stdout.write('\t[%s] %s%s ...%s\r' % (bar, percents, '%', status))
    if percents == 100:
        sys.stdout.write('\n')
    sys.stdout.flush()


def test_progress_bar():
    import time

    total = 1000
    i = 0
    while i < total:
        progress(i, total, status=f'Doing very long job {i}')
        time.sleep(0.2)  # emulating long-playing job
        i += 1


def get_query_params(url):
    return dict(parse.parse_qsl(parse.urlsplit(url).query))

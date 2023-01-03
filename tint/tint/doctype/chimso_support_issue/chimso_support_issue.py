# Copyright (c) 2021, Chimso XYZ and contributors
# For license information, please see license.txt

import re
from tint.tint.central.roles import add_role_permission
from tint.tint.utils import create_system_notification
from tint.tint.central.api import trigger_method, update_doc, insert_doc
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.permissions import update_permission_property
from frappe.utils.data import strip_html


class ChimsoSupportIssue(Document):
    def before_save(self):
        print("saving")
        if self.raised_by is None:
            self.raised_by = frappe.session.user

    def on_submit(self):
        data = self.as_dict()
        print("support iss dict", data, frappe.local.site)
        data.update({"site": frappe.local.site})
        data.update({"cust_ref_doc": self.name})
        data["issue_description"] = strip_html(data["issue_description"])
        pop_list = ["name", "owner", "modified", "modified_by",
                    "parent", "doctype", "autoname", "docstatus", "creation"]
        data = pop_from_dict(dict=data, pop_list=pop_list)
        # send to chimso
        # print('data', data)
        res = insert_doc("Customer Support Issue", data=data)
        print("insert issue res", res)
        if res.get("data"):
            ref_doc = res.get("data").get("name")
            res_data = pop_from_dict(dict=res.get("data"), pop_list=pop_list)

            for key, value in res_data.items():
                if hasattr(self, key) and key not in pop_list:
                    print(key, value)
                    frappe.db.set_value(
                        "Chimso Support Issue", self.name, key, value)

            frappe.db.set_value("Chimso Support Issue",
                                self.name, "ref_doc", ref_doc)
            frappe.db.set_value("Chimso Support Issue", self.name, "sent", 1)
            # print("final doc", self.as_dict())
            frappe.msgprint(
                _("Issue forwarded and saved successfully. Please be patient while we attend to your concerns. Thank you"))
        else:
            frappe.msgprint(_("Issue sync in progress..."))

    def on_update_after_submit(self):
        print("Updating after submit")
        users_to_notify = [self.raised_by]
        message = "{{ doc.name }} has been updated"
        subject = "Update on issue {{ doc.issue_id or doc.subject }}"
        self.reload()
        self.notify_update()
        create_system_notification(
            doc=self, users=users_to_notify, subject=subject, message=message)

    def on_cancel(self):
        # cancel on chimso
        res = trigger_method(data={"docname": self.ref_doc},
                             method_path="central.central.doctype.customer_support_issue.customer_support_issue.cancel_issue_by_user")
        if res.get("success"):
            frappe.msgprint(_(res.get("msg")))
        else:
            frappe.throw(_(res.get(
                "errMsg") or "Error occured while trying to cancel issue, please try again later."))


@frappe.whitelist()
def check_sent_status():
    """
    To make sure all issues are sent to chimso
    """
    # get all issues not sent to chimso
    issues_not_sent = frappe.get_list(
        "Chimso Support Issue", {"sent": 0, "submit": 1}, ["name"])
    print("issues not sent", issues_not_sent)
    for issue in issues_not_sent:
        print("issue name", issue)
        iss_doc = frappe.get_doc("Chimso Support Issue", issue.get("name"))
        iss_doc.on_submit()


@frappe.whitelist()
def update_all_issues():
    # check if customer support issues has been updated
    pass


def pop_from_dict(dict, pop_list=[]):
    for item in pop_list:
        if dict.get(item):
            dict.pop(item)
    return dict


@frappe.whitelist()
def update_issue(data):
    fields_to_update = ["priority_level", "expected_resolution_by", "status"]
    docname = data.get("cust_ref_doc") or data.get("name")
    if docname and frappe.db.exists("Chimso Support Issue", docname):
        for field in fields_to_update:
            if data.get(field):
                frappe.db.set_value("Chimso Support Issue",
                                    docname, field, data.get(field))
            else:
                print(field, "not found in update data")
        print("all fields updated")
        frappe.get_doc("Chimso Support Issue",
                       docname).on_update_after_submit()
        frappe.publish_realtime('new_comment_from_chimso', docname=docname)
        return {"success": True, "msg": "Issue updated successfully"}
    else:
        return {"success": False, "error": True, "errMsg": "Issue not found on customer site"}


@frappe.whitelist()
def install_default_permissions():
    role = 'All'
    permissions = [
        {'doctype': 'Issue Type', 'ptype': 'read', 'value': 1},
        {'doctype': 'Issue Type', 'ptype': 'if_owner', 'value': 1, 'update': 1},
        {'doctype': 'Issue Type', 'ptype': 'create', 'value': 1, 'update': 1},
        {'doctype': 'Issue Type', 'ptype': 'write', 'value': 1, 'update': 1},
        {'doctype': 'Issue Type', 'ptype': 'delete', 'value': 1, 'update': 1},
        {'doctype': 'Issue Priority', 'ptype': 'if_owner', 'value': 1},
        {'doctype': 'Issue Priority', 'ptype': 'read', 'value': 1, 'update': 1}
    ]
    for perm in permissions:
        add_role_permission(doctype=perm.get('doctype'), role=role,
                            ptype=perm.get('ptype'), value=perm.get('value'))

        print('permissions added successfully')


@frappe.whitelist()
def add_comment(doc):
    print('Create comment with', doc)
    subject = doc.get("reference_name")
    cs_issue = frappe.get_doc("Chimso Support Issue", {
                              "subject": subject})
    print("cs issue found", cs_issue)
    if not cs_issue:
        return {'error': True, 'errMsg': 'Issue not found'}
    # del doc["reference_name"]
    reference_owner = re.match(r'chimso(.*)?\)',
                               doc.get('content'), flags=re.IGNORECASE).group(0)
    doc.update({"doctype": "Comment", "reference_owner": reference_owner})
    comment = frappe.get_doc(doc)
    try:
        comment.insert()
        frappe.publish_realtime(
            'new_comment_from_chimso', docname=cs_issue.name)
        return {'error': False, 'success': True, 'msg': f'Comment created successfully for subject - {subject}'}
    except Exception as e:
        return {'error': True, 'errMsg': 'Comment creation failed', "e": e}


def sync_with_chimso(doc, method):
    print('Here', doc.as_json(), method)
    first_name = frappe.db.get_value('User', frappe.session.user, 'first_name')
    if doc.comment_type == 'Comment' and doc.reference_doctype == "Chimso Support Issue" and doc.comment_by and doc.published == 0:
        data = doc.as_dict()
        ref_subject = data.get("reference_name")
        user = data.get("comment_by") or first_name or frappe.session.user
        data["content"] = f"Client({user}): " + strip_html(data["content"])
        data["reference_doctype"] = "Customer Support Issue"
        data["reference_owner"] = ref_subject
        data['published'] = 1
        data["ref_subject"] = ref_subject
        pop_list = ["owner", "modified", "modified_by", "link_doctype",
                    "link_name", "reference_name", "__unsaved",
                    "parent", "doctype", "autoname", "docstatus", "creation"]
        data = pop_from_dict(dict=data, pop_list=pop_list)
        method_path = "central.central.doctype.customer_support_issue.customer_support_issue.add_comment"
        # send to chimso
        res = trigger_method(method_path=method_path, data={"doc": data})
        print("insert issue res", res)
        if res.get("message") and not res.get('message').get("error"):
            frappe.msgprint("Comment sent", alert=True)
        else:
            # TODO: Add to list of comments to sync
            frappe.msgprint(
                _("Issue sync failed, please try again later or contact support..."))


# def update_comment_on_chimso(doc, method):
#     print('comment updated on client', doc.as_json())
#     # send to chimso
#     # if method == 'on_update':
#     method_path = "central.central.doctype.customer_support_issue.customer_support_issue.update_comment"
#     data = {'subject': doc.reference_name, 'edited_by': doc.modified_by, 'content': strip_html(doc.content), 'method': 'from_client'}
#     res = trigger_method(method_path=method_path, data={"doc": data})
#     # frappe.publish_realtime('new_comment', docname=doc.name)

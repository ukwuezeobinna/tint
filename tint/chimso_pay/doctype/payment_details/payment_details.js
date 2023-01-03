// Copyright (c) 2021, Chimso XYZ and contributors
// For license information, please see license.txt

frappe.ui.form.on('Payment Details', {
	refresh: function(frm) {
		frm.add_custom_button(__("Update Status"), () => {
			frappe.dom.freeze()
			frappe.call("tint.chimso_pay.doctype.payment_details.payment_details.check_status_and_update", {docname: frm.docname}).then(r => {
				frm.reload_doc();
				frappe.dom.unfreeze()
			});
		})
	}
});

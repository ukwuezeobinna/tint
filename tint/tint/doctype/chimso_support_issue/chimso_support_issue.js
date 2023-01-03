// Copyright (c) 2021, Chimso XYZ and contributors
// For license information, please see license.txt
// doc.content.match(/chimso(.*)?\)/ig)[0]
frappe.ui.form.on('Chimso Support Issue', {
	onload: function(frm) {
		frappe.realtime.on('new_comment_from_chimso', () => {
			console.log('yes');
			frm.reload_doc();
			});
	},
});

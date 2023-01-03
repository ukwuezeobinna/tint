let adjustments_in_progress = [];

frappe.listview_settings['Price Adjustment'] = {
	onload(listview) {
		frappe.realtime.on('price_adjustment_progress', data => {
			if (!adjustments_in_progress.includes(data.price_adjustment)) {
				adjustments_in_progress.push(data.price_adjustment);
			}
		});
		frappe.realtime.on('price_adjustment_refresh', data => {
			adjustments_in_progress = adjustments_in_progress.filter(
				d => d !== data.price_adjustment
			);
			listview.refresh();
		});
	},
	get_indicator: function(doc) {
		var colors = {
			'Pending': 'orange',
			'Not Started': 'orange',
			'Partial Success': 'orange',
			'Incomplete': 'orange',
			'Success': 'green',
			'In Progress': 'orange',
			'Error': 'red',
      'Failed': 'red'
		};
		let status = doc.status;
		if (adjustments_in_progress.includes(doc.name)) {
			status = 'In Progress';
		}
		if (status == 'Pending') {
			status = 'Pending';
		}
		return [__(status), colors[status], 'status,=,' + doc.status];
	},
	formatters: {
		import_type(value) {
			return {
				'Insert New Records': __('Insert')
			}[value];
		}
	},
	hide_name_column: true
};

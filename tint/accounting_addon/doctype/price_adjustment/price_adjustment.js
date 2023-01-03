// Copyright (c) 2021, Chimso XYZ and contributors
// For license information, please see license.txt
var colors = {
	Pending: "orange",
	"Not Started": "orange",
	"Partial Success": "orange",
	Incomplete: "orange",
	Success: "green",
	"In Progress": "orange",
	Error: "red",
	Failed: "red",
};

var change_log_displayed = false;

frappe.ui.form.on("Price Adjustment", {
	setup(frm) {
		frappe.realtime.on("price_adjustment_refresh", ({ price_adjustment }) => {
			if (price_adjustment !== frm.doc.name) return;
			frappe.model.clear_doc("Price Adjustment", frm.doc.name);
			frappe.model.with_doc("Price Adjustment", frm.doc.name).then(() => {
				frm.refresh();
			});
		});
		frappe.realtime.on("price_adjustment_progress", (data) => {
			if (data.price_adjustment !== frm.doc.name) {
				return;
			}
			let percent = Math.floor((data.current * 100) / data.total);
			let seconds = Math.floor(data.eta);
			let minutes = Math.floor(data.eta / 60);
			let eta_message =
				// prettier-ignore
				seconds < 60
					? __('About {0} seconds remaining', [seconds])
					: minutes === 1
						? __('About {0} minute remaining', [minutes])
						: __('About {0} minutes remaining', [minutes]);

			let message;
			if (data.success) {
				let message_args = [data.current, data.total, eta_message];
				message =
					frm.doc.import_type === "Insert New Records"
						? __("Updating prices {0} of {1}, {2}", message_args)
						: __("Updating {0} of {1}, {2}", message_args);
			}
			if (data.skipping) {
				message = __("Skipping {0} of {1}, {2}", [
					data.current,
					data.total,
					eta_message,
				]);
			}
			frm.dashboard.show_progress(__("Import Progress"), percent, message);
			frm.page.set_indicator(__("In Progress"), "orange");

			// hide progress when complete
			if (data.current === data.total) {
				setTimeout(() => {
					frm.dashboard.hide();
					frm.refresh();
				}, 5000);
			}
		});

		// filter out already present items
		const listedItems = [];
		if (frm.doc.change_all === 0 && frm.doc.items) {
			frm.doc.items.forEach((row) => {
				if (row.item) {
					listedItems.push(row.item);
				}
			});
			frm.set_query("item", "items", () => {
				return {
					filters: {
						item_code: ["not in", listedItems],
					},
				};
			});
		}

		frm.trigger("update_indicators");
	},

	before_save: function (frm) {
		// clear amount field if percentage is selected and vice versa
		if (frm.doc.change_by === "Percentage" && frm.doc.amount_change) {
			frm.doc.amount_change = 0;
		} else if (
			frm.doc.change_by === "Fixed Amount" &&
			frm.doc.percentage_change
		) {
			frm.doc.percentage_change = 0;
		}
	},

	onload: function (frm) {
		// TODO: bug fix - find a proper fix from backend
		// use change_log to update new prices that did not show
		const change_log = frm.doc ? JSON.parse(frm.doc.change_log) : [];
		const validStatList = ["Success", "Incomplete", "Partial Success"];
		if (
			!frm.is_new() &&
			validStatList.some((stat) => stat === frm.doc.status) &&
			change_log.length > 0
		) {
			// check the change_log to find items that have no new_price displayed but already changed
			$.each(frm.doc.items || [], function (i, item) {
				if (
					item.new_price == 0 &&
					change_log.some(
						(record) =>
							(record.item_code === item.item ||
								record.docname === item.name) &&
							record.new_price !== item.new_price
					)
				) {
					const record = change_log.find(
						(record) =>
							(record.item_code === item.item ||
								record.docname === item.name) &&
							record.new_price !== item.new_price
					);
					const row = locals[item.doctype][item.name];
					row["new_price"] = record.new_price;
					if (record.status) row["status"] = record.status;
				}
			});
			frm.save();
			frm.refresh_field("items");
		}

		// To show log if any change was not successful
		if (change_log.some((record) => record.status !== "Success")) {
      change_log_displayed = true;
			frm.set_df_property("change_log", "hidden", 0);
		}
	},

	onload_post_render(frm) {
		// For duplicates of completed or incomplete pa
		if (frm.is_new() && frm.doc.status !== "Not Started") {
			frm.trigger("reset_status_for_new_form");
		}
		frm.trigger("update_primary_action");
	},

	reset_status_for_new_form(frm) {
		frm.set_value("status", "Not Started");
		frm.set_value("change_log", JSON.stringify([]));
		frm.dashboard.set_headline(__(""));
		// frm.dashboard.hide();
		if (frm.doc.items && frm.doc.items.some((row) => row.item)) {
			$.each(frm.doc.items || [], (i, item) => {
				const row = locals[item.doctype][item.name];
				row["status"] = "Not Started";
				row["old_price"] = undefined;
				row["new_price"] = undefined;
				frm.events.update_item(frm, item.doctype, item.name);
			});
		}
		frm.refresh_fields();
	},

	refresh(frm) {
		// frm.page.hide_icon_group();
		frm.trigger("update_indicators");
		frm.trigger("show_adjustment_status");
		const allow_error_export = [
			"Incomplete",
			"Partial Success",
			"Error",
			"Failed",
		];

		if (
			frm.doc.status === "Partial Success" ||
			frm.doc.status === "Incomplete"
		) {
			frm.add_custom_button(__("Retry Failed"), () =>
				frm.trigger("start_adjustment")
			);
		}
		if (allow_error_export.some((stat) => stat == frm.doc.status)) {
			frm.add_custom_button(__("Export Failed"), () =>
				frm.trigger("export_errored_rows")
			);
		}
	},

	export_errored_rows(frm) {
		open_url_post(
			"/api/method/tint.accounting_addon.doctype.price_adjustment.price_adjustment.download_errored_template",
			{
				docname: frm.doc.name,
			}
		);
	},

	update_indicators(frm) {
		const indicator = frappe.get_indicator(frm.doc);
		if (indicator) {
			frm.page.set_indicator(indicator[0], indicator[1]);
		} else {
			frm.page.clear_indicator();
		}
	},

	show_adjustment_status(frm) {
		let change_log = JSON.parse(frm.doc.change_log || "[]");
		let successful_records = change_log.filter((log) => log.success);
		let failed_records = change_log.filter((log) => !log.success);
		if (successful_records.length === 0 && frm.doc.status !== "Failed") return;

		let message;
		if (failed_records.length === 0) {
			let message_args = [
				successful_records.length,
				change_log[0].total || change_log.length,
			];
			message =
				successful_records.length > 1
					? __("Successfully updated {0} prices out of {1}.", message_args)
					: __("Successfully updated {0} price out of {1}.", message_args);
		} else {
      const no_of_mismatch = failed_records.filter((log) => log.status === "Price Mismatch").length;
			let message_args = [
				successful_records.length,
				change_log[0].total || change_log.length,
        no_of_mismatch
			];
			message =
				no_of_mismatch > 0
					? __("Successfully updated {0} prices out of {1}. <br> {2} price mismatch.", message_args)
					: __("Successfully updated {0} price out of {1}.", message_args);
      // add button to toggle showing change_log
      frm.add_custom_button(__("Toggle Log"), () => {
        change_log_displayed = !change_log_displayed;
        frm.toggle_display("change_log", change_log_displayed ? 1 : 0)
      });
		}
		frm.dashboard.set_headline(message);
	},

	update_primary_action(frm) {
		if (frm.is_dirty()) {
			frm.enable_save();
			return;
		}
		if (frm.doc.status !== "Success") {
			if (frm.doc.status === "In Progress" || frm.doc.status === "Pending") {
				frm.disable_save();
			} else if (!frm.is_new()) {
				let label =
					frm.doc.status === "Not Started" ? __("Start Change") : __("Retry");
				frm.page.set_primary_action(label, () =>
					frm.events.start_adjustment(frm)
				);
			} else {
				frm.trigger("set_primary_action_to_save");
			}
		} else {
			frm.disable_save();
		}
	},

	set_primary_action_to_save(frm) {
		frm.page.set_primary_action(__("Save"), () => frm.save());
	},

	status: function (frm) {
		frm.trigger("update_indicators");
	},

	update_indicators(frm) {
		const status = frm.doc.status;
		frm.page.set_indicator(__(status), colors[status]);
	},

	start_adjustment(frm) {
		frappe.dom.freeze();
		frm
			.call({
				method: "form_start_adjustment",
				args: { docname: frm.doc.name },
				btn: frm.page.btn_primary,
			})
			.then((r) => {
				frappe.dom.unfreeze();
				// if false, it was already in queue
				if (r.message === true || r.message === false) {
					frm.disable_save();
					// To see an update after 5 sec
					setTimeout(() => frm.reload_doc(), 2000);
				}
			});
	},

	after_save: function (frm) {
		frm.trigger("update_primary_action");
		setTimeout(() => frm.reload_doc(), 1000);
	},

	percentage_change: function (frm) {
		frm.trigger("set_primary_action_to_save");

		if (frm.doc.change_all === 0) {
			$.each(frm.doc.items || [], function (i, item) {
				const row = locals[item.doctype][item.name];
				row["percentage_change"] = frm.doc.percentage_change;
			});
			frm.refresh_fields();
		}
	},

	change_all: function (frm) {
		frm.trigger("reset_status_for_new_form");
	},

	change_by: function (frm) {
		frm.trigger("set_primary_action_to_save");

		if (frm.doc.change_all === 0) {
			$.each(frm.doc.items || [], function (i, item) {
				const row = locals[item.doctype][item.name];
				row["percentage_change"] =
					frm.doc.change_by === "Percentage" ? frm.doc.percentage_change : 0;
			});
			frm.refresh_fields();
		}
	},

	update_item(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		frappe
			.call("frappe.client.get", {
				doctype: "Item Price",
				filters: { item_code: row.item },
			})
			.then((r) => {
				row["old_price"] = r.message.price_list_rate;
				row["currency"] = r.message.currency;
				row["item_price"] = r.message.name;
				if (frm.doc.change_by === "Percentage" && frm.doc.percentage_change) {
					row["percentage_change"] = frm.doc.percentage_change;
				} else {
					row["percentage_change"] = 0;
				}
				frm.refresh_fields();
			});
	},

	items_add: function (frm) {
		frm.trigger("set_primary_action_to_save");
	},

	item_group: function (frm) {},

	price_list: function (frm) {
		frm.trigger("set_primary_action_to_save");
	},
});

frappe.ui.form.on("Item To Adjust", {
	item: function (frm, cdt, cdn) {
		frm.events.update_item(frm, cdt, cdn);
	},
});

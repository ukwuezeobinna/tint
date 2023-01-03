frappe.provide("frappe.dn.variables");
frappe.ui.form.on("Delivery Note", {
  onload(frm) {
    frappe.dn.variables = {};
    frappe.dn.variables.assigned_warehouses = [];
    try {
      if (/administrator/i.test(frappe.user) === false) {
        frappe
          .call("frappe.client.get", {
            doctype: "Warehouse Staff",
            filters: { user: frappe.user.name },
          })
          .then((res) => {
            if (res.message) {
              let { warehouses } = res.message;
              warehouses = warehouses.map((w) => w.warehouse);
              frappe.dn.variables.assigned_warehouses = warehouses || [];
              console.log("wh", frappe.dn.variables.assigned_warehouses);
              if (warehouses.length > 0) console.log("about to set filter");
              frm.set_query("warehouse", "items", () => {
                console.log("returning filter", warehouses);
                return {
                  filters: {
                    //company: 'Chimso',
                    name: ["in", frappe.dn.variables.assigned_warehouses],
                  },
                };
              });
            }
          });
      }
    } catch (err) {
      console.error(err);
    }
  },
  // To ensure only qt of assigned warehouses are saved
  before_save(frm) {
    console.log("as wh", frappe.dn.variables.assigned_warehouses);
    if (/administrator/i.test(frappe.user) === false) {
      if (frappe.dn.variables.assigned_warehouses.length > 0) {
        const items = frm.doc.items;
        console.log("items", items);
        if (
          items.every((item) =>
            frappe.dn.variables.assigned_warehouses.some(
              (wh) => wh === item.warehouse
            )
          ) === false
        ) {
          // items do not match assigned warehouse
          frappe.throw(
            `Insufficient Permission to item warehouse. ${frm.doc.doctype}s allowed only for warehouses: ${frappe.dn.variables.assigned_warehouses}`
          );
        }
      }
    }
  },
});

frappe.provide("frappe.qt.variables");
frappe.ui.form.on("Quotation", {
  setup(frm) {
    // your code here
    // console.log(frappe.user)
    frappe.qt.variables = {};
    frappe.qt.variables.assigned_warehouses = [];
    try {
      if (/administrator/i.test(frappe.user) === false) {
        frappe
          .call("frappe.client.get", {
            doctype: "Warehouse Staff",
            filters: { user: frappe.user.name },
          })
          .then((res) => {
            //alert(`${res.message.warehouses}`);
            if (res.message) {
              let { warehouses } = res.message;
              warehouses = warehouses.map((w) => w.warehouse);
              //  alert(warehouses[0]);
              frappe.qt.variables.assigned_warehouses = warehouses || [];
              console.log("wh", frappe.qt.variables.assigned_warehouses);
              if (warehouses.length > 0)
                frm.set_query("warehouse", "items", () => {
                  return {
                    filters: {
                      //company: 'Chimso',
                      name: ["in", frappe.qt.variables.assigned_warehouses],
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
    console.log("as wh", frappe.qt.variables.assigned_warehouses);
    if (/administrator/i.test(frappe.user) === false) {
      if (frappe.qt.variables.assigned_warehouses.length > 0) {
        const items = frm.doc.items;
        console.log("items", items);
        if (
          items.every((item) =>
            frappe.qt.variables.assigned_warehouses.some(
              (wh) => wh === item.warehouse
            )
          ) === false
        ) {
          // items do not match assigned warehouse
          frappe.throw(
            `Insufficient Permission to item warehouse. ${frm.doc.doctype}s allowed only for warehouses: ${frappe.qt.variables.assigned_warehouses}`
          );
        }
      }
    }
  },
});

frappe.ui.form.on("Quotation Item", {
  refresh(frm) {
    // your code here
  },
});

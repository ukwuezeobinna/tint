import frappe

def execute():
  if frappe.local.site not in ["app.chimso.xyz", "chimso.xyz", "docs.chimso.xyz"] and frappe.db.exists("Navbar Item", {"item_label": "Report an Issue"}):
    item = frappe.get_doc("Navbar Item", {"item_label": "Report an Issue"})
    item.delete()

import frappe

def execute():
  dropdowns = {
    "Documentation": "https://docs.chimso.xyz"
  }
  for key, value in dropdowns.items():
    try:
      item = frappe.get_doc("Navbar Item", {"item_label": key})
      if item:
        item.route = value
        item.save()
    except frappe.exceptions.DoesNotExistError:
      print("Navbar Item not found", key)
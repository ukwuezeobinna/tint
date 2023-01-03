import frappe

def execute():
  navbar_settings = frappe.get_single("Navbar Settings")
  navbar_settings.append("help_dropdown", {
    "item_label": "Chimso Support",
    "item_type": "Route",
    "route": "/app/chimso-support-issue"
  })
  navbar_settings.save()
# Copyright (c) 2021, Chimso XYZ and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils.data import flt

class ItemToAdjust(Document):
  def adjust_price(self, price_list, percentage=0, amount=0, pa=None):
    # print("adjust price with", percentage or amount, "{}".format("%" if percentage else ""), ". Current status is", self.status)
    if self.status != "Success" or self.status != "Price Mismatch":
      current_price = frappe.db.get_value(
          "Item Price", {"item_code": self.item, "price_list": price_list}, "price_list_rate")
      if flt(self.old_price) == flt(current_price):
        # ("prices are same")
        if percentage:
          # use percentage
          self.new_price = flt(self.old_price)*(1 + percentage/100)
          self.percentage_change = percentage
        elif amount:
          self.new_price = flt(self.old_price) + flt(amount)
          self.percentage_change = ((self.new_price - self.old_price)/self.old_price) * 100
          # print("using fixed rate", self.old_price, self.new_price)
        frappe.db.set_value("Item Price", self.item_price, "price_list_rate", self.new_price)
        self.status = "Success"
      else:
        # print("price mismatch")
        self.status = "Price Mismatch"
      self.save()
    return self.status, self.new_price

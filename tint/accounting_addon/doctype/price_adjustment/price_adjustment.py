# Copyright (c) 2021, Chimso XYZ and contributors
# For license information, please see license.txt

from frappe.core.page.background_jobs.background_jobs import get_info
from tint.tint.utils import progress
import json
import frappe
from frappe import _
from frappe.core.doctype.data_import.importer import INVALID_VALUES
from frappe.model.document import Document
from frappe.utils import random_string, update_progress_bar
from frappe.utils.background_jobs import enqueue


class PriceAdjustment(Document):
    def validate(self):
        self.validate_change_validity()
        self.validate_price_list()
        self.validate_item_group_amount()

    def validate_change_validity(self):
        if (self.change_by == "Percentage" and not self.percentage_change):
            frappe.throw(_("Please specify a valid percentage"))
        elif self.change_by == "Fixed Amount" and not self.amount_change:
            frappe.throw(_("Please specify a valid amount"))
    
    def validate_item_group_amount(self):
      if self.change_all == 1 and self.item_group != None:
        list_of_items = frappe.db.get_all("Item", {"item_group": self.item_group}, ["item_code", "name"])
        amt_of_items = len([item for item in list_of_items if frappe.db.exists("Item Price", {"item_code": item.get("item_code"), "price_list": self.price_list})])
        if amt_of_items == 0:
          frappe.throw(_(f"There are no items for item group of {self.item_group} in {self.price_list}. Please create items first or choose another item group"))
    
    def get_items_count(self):
      if self.change_all == 0:
        items = self.items
      else:
        items = frappe.get_all("Item Price", filters={"price_list": self.price_list}, fields=[
                              "item_code", "price_list_rate", "currency"])
        if self.item_group:
          print("selecting item groups items", len(items))
          items = [item for item in items if frappe.db.get_value("Item", {"item_code": item.get(
              "item_code"), "item_group": self.item_group}, "item_code") == item.get("item_code")]
          print("final item groups items", len(items))
        print(f"change all items {self.name} {self.item_group or ''}")
      return len(items)

    def validate_price_list(self):
      price_list_items = frappe.db.count("Item Price", {"price_list": self.price_list})
      if price_list_items == 0:
        frappe.throw(_(f"There are no items for price list of {self.price_list}. Please select another price list"))


    def start_adjustment(self):
        from frappe.core.page.background_jobs.background_jobs import get_info
        from frappe.utils.scheduler import is_scheduler_inactive

        if is_scheduler_inactive() and not frappe.flags.in_test:
            frappe.throw(
                _("Scheduler is inactive. Cannot proceed with price adjustments."), title=_("Scheduler Inactive")
            )
        enqueued_jobs = [d.get("job_name") for d in get_info()]
        amt_of_items = self.get_items_count()
        print("jobs", len(enqueued_jobs), self.name, amt_of_items)
        self.db_set("status", "Pending")
        if self.name not in enqueued_jobs:
            enqueue(
                start_adjustment,
                queue="long" if amt_of_items > 1000 else "default",
                timeout=6000,
                event="price_adjustment",
                job_name=self.name,
                docname=self.name,
                is_async=True if amt_of_items > 100 else False,
                # now=False or frappe.conf.developer_mode or frappe.flags.in_test,
            )
            # self.db_set("status", "In Progress")
            print("returning response")
            return True

        return False
    
    def export_errored_rows(self):
      from frappe.utils.csvutils import build_csv_response
      
      change_log = frappe.parse_json(self.change_log or "[]")
      failures = [log for log in change_log if not log.get("success")]

      header_row = ["success", "exception", "item", "current_index", "old_price", "message"]
      rows = [header_row]
      # for f in failures:
      rows += [[f.get(key, None) for key in header_row] for f in failures]
      print("rows", rows)
      build_csv_response(rows, self.doctype)


@frappe.whitelist()
def form_start_adjustment(docname):
    return frappe.get_doc("Price Adjustment", docname).start_adjustment()


def start_adjustment(docname):
    """This method runs in background job"""
    pa = frappe.get_doc("Price Adjustment", docname)
    print("sa started", pa.change_all, pa.name)
    pa.db_set("status", "In Progress")
    # current_index = 0
    if pa.change_log:
      # remove failed
      change_log = frappe.parse_json(pa.change_log)
      change_log = [
          log for log in change_log if (log.get("success") or log.get("status") == "Price Mismatch")]
      pa.db_set("change_log", json.dumps(change_log))

    # else:
    #     change_log = []
    if pa.change_all==0:
      items = pa.items 
    else:
      items = frappe.get_all("Item Price", filters={"price_list": pa.price_list}, fields=["item_code", "price_list_rate", "currency"])
      progress(0, len(items), f"change all items {pa.name} {pa.item_group or ''}")
    # unsuccessful_changes = []
    if pa.item_group:
      print("selecting item groups items", len(items))
      items = [item for item in items if frappe.db.get_value("Item", {"item_code": item.get("item_code"), "item_group": pa.item_group}, "item_code") == item.get("item_code")]
      print("final item groups items", len(items))
    batch_size = frappe.conf.price_adjustment_batch_size or 500

    try:
      for batch_index, batched_items in enumerate(
            frappe.utils.create_batch(items, batch_size)
        ):
        progress(0, len(items), f"batch {batch_index}")
        batch_name = f"{pa.name}-batch-{batch_index}"
        # if batch_name not in enqueued_jobs:
        print('starting', batch_name)
        handle_batch(pa=pa, batched_items=batched_items, batch_index=batch_index, batch_size=batch_size, total=len(items))
      change_log = frappe.parse_json(pa.change_log)
      failures = [log for log in change_log if not log.get("success")]
      mismatched = [log for log in failures if log.get("status") == "Price Mismatch"]
      
      if len(failures) == len(mismatched):
        status = "Failed"
      elif len(failures) == len(batched_items):
        status = "In Progress"
      elif len(failures) > 0:
        status = "Incomplete"
      else:
        status = "Success"
      pa.db_set("status", status)
    except Exception as e:
        print("error", e, frappe.get_traceback())
        frappe.db.rollback()
        pa.db_set("status", "Error")
        frappe.log_error(title=docname)
        change_log = frappe.parse_json(pa.change_log)
        change_log.append(
            frappe._dict(
                success=False,
                exception=frappe.get_traceback(),
                # current_index = current_index,
                messages=frappe.local.message_log,
                total=len(items),
            )
        )
        frappe.clear_messages()
        pa.db_set("change_log", json.dumps(change_log))
    frappe.publish_realtime("price_adjustment_refresh", {
                            "price_adjustment": pa.name})

def process_item(item, pa):
  """
  To process item before price adjustment. Makes sure that item is in items table before adjustment in case of "change_all=1"
  param item(ItemToAdjust or dict): the item that is to be process, dt: "Item To Adjust", "Item Price"
  param pa(PriceAdjustment)
  param change_all: determines whether to create an ItemToAdjust entry in pa
  returns item (ItemToAdjust)
  """
  if pa.change_all == 1 and not frappe.db.exists("Item To Adjust", {"parent": pa.name, "item": item.get("item_code") or item.get("item")}):
    pa.append("items", {
      "doctype": "Item To Adjust",
      "item": item.get("item_code"),
      "old_price": item.get("price_list_rate"),
      "new_price": 0,
      "currency": item.get("currency"),
      "percentage_change": pa.percentage_change or 0,
      "status": "Not Started",
      "item_price": frappe.db.get_value("Item Price", {"item_code": item.get("item_code")})
    })
    pa.save()
  return frappe.get_doc("Item To Adjust", {"item": item.get("item_code") or item.get("item")})

def handle_batch(pa, batched_items, batch_index, batch_size, total):
  status = "In Progress"
  pa.db_set("status", status)
  if pa.change_log:
    change_log = frappe.parse_json(pa.change_log)
  else:
      change_log = []
  for i, item in enumerate(batched_items):
    # add item to pa if it does not exist
    current_index = (i + 1) + (batch_index * batch_size)
    if item.status in ["Success", "Price Mismatch"]:
      print("Skipping imported row for", item.get(
          "item_code") or item.get("item"))
      if total > 5:
        frappe.publish_realtime(
          "price_adjustment_progress",
          {
            "current": current_index,
            "total": total,
            "docname": pa.name,
            "price_adjustment": pa.name,
            "success": True,
          },
        )
      continue

    try:
      pa.db_set("change_log", json.dumps(change_log))
      item = process_item(item, pa=pa)
      # print("current item", item)
      frappe.log(f"current item{item.name}")
      new_status, new_price = frappe.get_doc("Item To Adjust", item.name).adjust_price(
        percentage=pa.percentage_change,
        amount=pa.amount_change,
        price_list=pa.price_list
      )

      progress(current_index, total, f"new status {new_status} {new_price}")
      frappe.publish_realtime(
        "price_adjustment_progress",
        {
          "current": current_index,
          "total": total,
          "docname": pa.name,
          "price_adjustment": pa.name,
          "success": True,
        },
      )
      # check if item is already present in the log and remove
      change_log = [record for record in change_log if record.get("item_code") != item.item]
      change_log.append(
        frappe._dict(
          success=new_status == "Success", docname=item.name,
          status=new_status,
          item_code=item.item,
          old_price=item.old_price,
          new_price=new_price,
          total=total,
        )
      )
      frappe.db.commit()
    except Exception as e:
      print("error", e, frappe.get_traceback())
      frappe.db.rollback()
      pa.db_set("status", "Error")
      frappe.log_error(title=pa.name)
      change_log.append(
        frappe._dict(
          success=False,
          exception=frappe.get_traceback(),
          current_index = current_index,
          messages=frappe.local.message_log,
          total=total,
        )
      )
      frappe.clear_messages()
    # set status
    pa.db_set("change_log", json.dumps(change_log))
    

def test_batch():
  payloads = frappe.get_all("Currency", fields=["name", "currency_name", "enabled"])
  batch_size = frappe.conf.price_adjustment_batch_size or 100

  print("payload", len(payloads))
  print("batches", frappe.utils.create_batch(payloads, batch_size))
  for batch_index, batched_payloads in enumerate(
      frappe.utils.create_batch(payloads, batch_size)
  ):
    print("current batch", batch_index, batched_payloads)
    for i, payload in enumerate(batched_payloads):
      # doc = payload.doc
      # row_indexes = [row.row_number for row in payload.rows]
      current_index = (i + 1) + (batch_index * batch_size)
      print("payload in batch", i, payload)

def generate_random_items(amount=100, naming_series="It-", item_group="All Item Groups", rate=0, stock_uom="Nos"):
  """
  To generate random items, generally for testing purposes
  param amount: number of items to create
  param naming_series: just a simple prefix for the items, default = "It-"
  param item_group: item group for the item, defaults to "All Item Group"
  param rate: standard rate
  """
  for i in range(1, amount + 1):
    # print(i)
    create_item(i, naming_series, item_group, rate, stock_uom, amount)


def create_item(i, naming_series, item_group, rate, stock_uom, amount):
  item_code = naming_series + random_string(4).lower() + f"-{i}"
  progress(count=i, total=amount, status=f"item {i} - {item_code}")
  if not frappe.db.exists("Item", {"item_code": item_code}):
    item = frappe.get_doc({
      "doctype": "Item",
      "item_code": item_code,
      "item_group": item_group,
      "standard_rate": rate + i if rate == 0 else rate,
      "stock_uom": stock_uom
    })
    # progress(count=i, total=amount, status=f"inserting - {item_code}")
    item.insert()
    progress(count=i, total=amount, status=f"inserted - {item_code}")
  else: create_item(i, naming_series, item_group, rate)

def check_incomplete_adjustments():
  pa_list = frappe.get_all("Price Adjustment", {"status": ["in", ["In Progress", "Pending"]]})
  for pa in pa_list:
    form_start_adjustment(pa)

def get_item_group_amount(item_group):
  return len(frappe.get_all("Item", {"item_group": item_group}))


@frappe.whitelist()
def download_errored_template(docname):
	pa = frappe.get_doc("Price Adjustment", docname)
	pa.export_errored_rows()

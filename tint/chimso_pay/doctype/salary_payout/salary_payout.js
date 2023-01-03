// Copyright (c) 2021, Chimso XYZ and contributors
// For license information, please see license.txt

const keywordMap = {
  PIN: "PIN",
  AVS_VBVSECURECODE: "address",
  NOAUTH_INTERNATIONAL: "address",
  AVS_NOAUTH: "address",
};

let docname;
let txRef;
let flwRef;

const make_payouts = () => {
  frm = window.frm;
  // get fee
  // frappe.dom.freeze();
  if (frm.doc.awaiting_confirmation)
    return frappe.throw(
      "Awaiting payment confirmation. Please try again later"
    );
  if (
    frm.doc.deposit_amount <= 0 ||
    frm.doc.deposit_amount < frm.doc.total_amount
  ) {
    frappe.throw("Insufficient balance, please fund the account and try again");
    return;
  }
  frappe.call({
    method: "tint.chimso_pay.get_balance",
    args: {
      currency: "NGN",
    },
    callback: function (r) {
      console.log(r.message);
      if (r.message.error)
        return frappe.throw("Error occurred while trying to get balance");
      const result = r.message.message;
      console.log(result);
      const balance = result.data.available_balance;
      // frappe.msgprint(`Available balance is ${result.currency} ${balance}`);
      if (balance < frm.doc.deposit_amount) {
        frappe.throw(
          "Insufficient balance, please fund the account and try again"
        );
      } else {
        frm.call("make_payout").then((r) => {
          frappe.msgprint(r.message.message);
        });
      }
    },
  });
}

const verify_charge = (txRef) => {
  frappe.call({
    method: "tint.chimso_pay.verify_charge",
    args: {
      txRef,
      docname,
    },
    callback: function (r) {
      console.log("result", r);
      const res = r.message;
      if (res.error === false && res.txRef) {
        // verify charge
        frappe.show_alert(
          {
            message: __("Payment verified successfully"),
            indicator: "green",
          },
          5
        );
        frappe.msgprint(res["msg"]);
        // Prompt to proceed with payout
      }
    },
  });
};

const validate_card_payment = (flwRef, otp) => {
  frappe.dom.freeze()
  console.log(flwRef, otp);
  frappe.call({
    method:
      "tint.chimso_pay.doctype.salary_payout.salary_payout.validate_payment",
    args: {
      otp,
      flwRef,
      docname,
    },
    callback: function (r) {
      frappe.dom.unfreeze();
      console.log("result", r);
      const res = r.message;
      frappe.show_alert(
        {
          message: __("Payment validation complete"),
          indicator: "green",
        },
        5
      );
      if (res.error === false && res.txRef && res.status === "success") {
        // verify charge
        // verify_charge(txRef);
        frappe.show_alert(
          {
            message: __("Payment successful"),
            indicator: "green",
          },
          15
        );
        // frm.refresh();
        frm.reload_doc();
        // Prompt to proceed with payout
        frappe.confirm(
          "Proceed with payout?",
          () => {
            // action to perform if Yes is selected
            make_payouts(frm);
          },
          () => {
            // action to perform if No is selected
            frappe.msgprint("");
          }
        );
      }
    },
    error: (r) => {
      frappe.dom.unfreeze();
      console.log("error occured here");
    },
  });
};

const initialize_card_payment = (
  card_number,
  card_cvc,
  card_month,
  card_year,
  amount,
  suggestedAuth = null,
  pin = null,
  address = null
) => {
  frappe.dom.freeze()
  frappe.call({
    method:
      "tint.chimso_pay.doctype.salary_payout.salary_payout.initialize_payment",
    args: {
      card_cvc,
      month: card_month,
      card_number,
      year: card_year,
      suggestedAuth,
      pin,
      address,
      amount,
      docname,
    },
    callback: function (r) {
      frappe.dom.unfreeze();
      console.log(r);
      const rslt = r.message;
      if (Object.entries(rslt).length === 0 || rslt.error === true) {
        frappe.throw(
          rslt.errMsg ||
            "Error occurred while trying to initialize payment, please try again later."
        );
        return false;
      }
      const res = rslt.message || rslt;
      console.log("res", res);
      if (res["suggestedAuth"]) {
        suggestedAuth = res["suggestedAuth"];
        const auth = keywordMap[suggestedAuth];
        if (/pin/i.test(auth)) {
          let pinPrompt = frappe.prompt(
            {
              label: "Card Pin",
              fieldname: "card_pin",
              fieldtype: "Int",
              reqd: 1,
            },
            (values) => {
              initialize_card_payment(
                card_number,
                card_cvc,
                card_month,
                card_year,
                amount,
                (suggestedAuth = "PIN"),
                (pin = values.card_pin)
              );
            },
            "Enter Card Pin",
            "Proceed"
          );
          pinPrompt.show();
        } else if (auth === "address") {
          frappe.msgprint("This card not supported at the moment");
        }
      } else if (res["validationRequired"] === true) {
        if (res["authUrl"]) {
          // console.log("auth url present", res.authUrl);
          window.open(res.authUrl, "_blank");
        }
        // console.log("requesting otp");
        let otpPrompt = frappe.prompt(
          {
            label: "Enter OTP",
            fieldname: "otp",
            fieldtype: "Int",
            reqd: 1,
          },
          (values) => {
            try {
              flwRef = res["flwRef"];
              validate_card_payment(res["flwRef"], values.otp);
            } catch (error) {
              frappe.throw(error.message);
            }
          },
          "Please Enter OTP sent",
          "Confirm OTP and Proceed"
        );
        otpPrompt.show();
      } else if (res["error"] === true) {
        frappe.throw(`Card Charge Failed. ${res[errMsg]}`);
      }
    },
    error: (r) => {
      frappe.dom.unfreeze();
      console.log("error occured here");
    },
  });
};

frappe.ui.form.on("Salary Payout", {
  refresh: function (frm) {
    window.frm = frm;
    docname = frm.doc.name;
    console.log(frm);
    if (frm.doc.docstatus === 1 && frm.doc.transfer_queued === 0) {
      // i.e. document has been submitted
      // if (frm.fields_dict.deposit_amount.value==0) {
      // frm.add_custom_button(
      //   __("Card Deposit"),
      //   function () {
      //     // get fee
      //     frappe.dom.freeze();
      //     frappe.call({
      //       method: "tint.chimso_pay.get_payment_fee",
      //       // args: {
      //       // 	currency: "NGN"
      //       // },
      //       callback: function (r) {
      //         frappe.dom.unfreeze();
      //         console.log(r.message);
      //         const data = r.message.message;
      //         if (data.status === "success") {
      //           const fee = data.data[0].fee;
      //           const total_fees = frm.doc.salary_slips.length * Number(fee);
      //           // frm.set_value("fees", total_fees);
      //           // frm.save();
      //           const total_amount = frm.doc.total_amount;
      //           const total_deposit = total_fees + total_amount;
      //           frappe.msgprint({
      //             title: __("Notification"),
      //             message: __(
      //               `Deposit ${total_deposit} ${data.currency}. This include transfer charges of ${data.data[0].fee} ${data.currency}. Are you sure you want to proceed?`
      //             ),
      //             primary_action: {
      //               label: "Proceed",
      //               action(values) {
      //                 console.log(values);
      //                 // collect card details
      //                 let cardForm = frappe.prompt(
      //                   [
      //                     {
      //                       label: "Card Number",
      //                       fieldname: "card_number",
      //                       fieldtype: "Int",
      //                       reqd: 1,
      //                       // value: 5199110725564550
      //                     },
      //                     {
      //                       label: "Expiry Date",
      //                       fieldname: "expiry_date",
      //                       fieldtype: "Data",
      //                       placeholder: "mm/yyyy",
      //                       pattern: "(0[1-9]|10|11|12)/20[0-9]{2}$",
      //                       reqd: 1,
      //                       columns: 2,
      //                     },
      //                     {
      //                       label: "CVC",
      //                       fieldname: "cvc",
      //                       fieldtype: "Data",
      //                       placeholder: "123",
      //                       max: 3,
      //                       reqd: 1,
      //                       columns: 1,
      //                     },
      //                   ],
      //                   (values) => {
      //                     console.log(values);
      //                     const rxdate = /(0[1-9]|10|11|12)\/20[0-9]{2}$/;
      //                     const rxcvc = /[0-9]{3,3}/;
      //                     const rxcardnum = /[0-9]{12,16}/;
      //                     // validate
      //                     if (rxcardnum.test(values.card_number) === false) {
      //                       frappe.throw(
      //                         "Invalid card number, card number must contain only numbers"
      //                       );
      //                     } else if (
      //                       rxdate.test(values.expiry_date) === false
      //                     ) {
      //                       frappe.throw("Invalid date");
      //                     } else if (
      //                       rxcvc.test(values.cvc) === false ||
      //                       values.cvc.length !== 3
      //                     ) {
      //                       frappe.throw("Invalid CVC");
      //                     } else {
      //                       // all values are valid
      //                       const expiry_date = `${values.expiry_date}`.split(
      //                         "/"
      //                       );
      //                       console.log(expiry_date);
      //                       // init payment with total_deposit
      //                       try {
      //                         initialize_card_payment(
      //                           values.card_number,
      //                           values.cvc,
      //                           expiry_date[0],
      //                           expiry_date[1],
      //                           total_deposit
      //                         );
      //                       } catch (error) {
      //                         console.log("here", error);
      //                         // frappe.
      //                         frappe.throw(error);
      //                       }
      //                       // validate card charge
      //                       // verify payment
      //                     }
      //                   },
      //                   "Card Details",
      //                   "Proceed with payment"
      //                 );
      //                 cardForm.show();
      //                 // turn off msgprint modal
      //                 const msgPrintCloseBtn = document.querySelector(
      //                   ".msgprint-dialog .btn-modal-close"
      //                 );
      //                 msgPrintCloseBtn.click();
      //               },
      //             },
      //           });
      //         } else {
      //           frappe.dom.unfreeze();
      //           frappe.throw(
      //             "Error occurred while trying to get fees. Please try again later."
      //           );
      //         }
      //       },
      //     });
      //   },
      //   __("Make Deposit")
      // );
      frm.add_custom_button(
        __("Bank Transfer"),
        function () {
          frappe.dom.freeze();
          frappe.call({
            method: "tint.chimso_pay.get_payment_fee",
            // args: {
            // 	currency: "NGN"
            // },
            callback: function (r) {
              frappe.dom.unfreeze();
              console.log(r.message);
              const data = r.message.message;
              if (data.status === "success") {
                const fee = data.data[0].fee;
                const total_fees = frm.doc.salary_slips.length * Number(fee);
                // frm.set_value("fees", total_fees);
                // frm.save();
                const total_amount = frm.doc.total_amount;
                const total_deposit = total_fees + total_amount;

                frappe.call({
                  method: "tint.chimso_pay.get_topup_account",
                  // args: {
                  // 	currency: "NGN"
                  // },
                  callback: function (r) {
                    console.log(r.message);
                    if (r.message.error)
                      return frappe.throw(
                        "Error occurred while trying to get balance"
                      );
                    const result = r.message ? r.message.message : r.message;
                    console.log(result);
                    if (result && result.hasOwnProperty("account_name")) {
                      if (frm.doc.awaiting_confirmation) {
                        frappe.msgprint(
                          "Payment awaiting confirmation, please try again later"
                        );
                      } else {
                        frappe.confirm(
                          `Account Details: <br> 
														${result.account_name} <br>
														${result.account_number} <br>
														${result.bank_name} <br>
		
														Total Deposit: ${total_deposit} ${data.currency}. <br>
														This include transfer charges of ${total_fees} ${data.currency}.
		
														Payment made, Proceed?
														`,
                          () => {
                            // make transfer claim
                            frappe.call({
                              method:
                                "tint.chimso_pay.doctype.salary_payout.salary_payout.transfer_claim",
                              args: {
                                docname: frm.doc.name,
                                amount: frm.doc.total_deposit || total_deposit,
                              },
                              callback: (r) => {
                                console.log(r);
                                frm.reload_doc();
                                if (r.message.success) {
                                  frappe.msgprint(r.message.msg);
                                } else {
                                  frappe.throw(r.message.errMsg);
                                }
                              },
                            });
                            // proceed after comfirmation
                          },
                          () => {
                            frappe.msgprint(
                              "Thank You. To proceed, please make payment via transfer or card payment to complete salary payout"
                            );
                          }
                        );
                      }
                    } else {
                      frappe.msgprint(
                        `Sorry Account details not available at the moment.<br> Please try again later`
                      );
                    }
                  },
                });
              }
            },
          });
        },
        __("Make Deposit")
      );
      if (frm.doc.transfer_queued === 0) {
				frm.add_custom_button(__("Make Payouts"), make_payouts);
			}
      
    }
    if (frm.doc.docstatus === 1 && frm.doc.verified_payment) {
      frm.add_custom_button(__("Update Status"), () => {
        frappe.dom.freeze();
        try {
          frappe
            .call(
              "tint.chimso_pay.doctype.salary_payout.salary_payout.update_payout_status",
              {docname}
            )
            .then((r) => {
              frm.reload_doc();
              frappe.dom.unfreeze();
            });
        } catch (error) {
          frappe.dom.unfreeze();
        }
      });
    }
  },
});

frappe.ui.form.on(
  "Payout Receiver Details",
  "salary_slip",
  function (frm, cdt, cdn) {
    var d = locals[cdt][cdn];
    frappe.db.get_value(
      "Salary Slip",
      { name: d.salary_slip },
      ["employee", "base_net_pay"],
      function (value) {
        console.log("employee name", value);
        // get the bank details
        frappe.db.get_value(
          "Employee",
          { name: value.employee },
          ["bank_name", "bank_ac_no"],
          function (values) {
            console.log("bank details", values);
            d.bank_name = values.bank_name;
            d.bank_account = values.bank_ac_no;
            console.log("base_net_pay", value.base_net_pay);
            if (value.base_net_pay >= 100) {
              d.net_pay = value.base_net_pay;
            } else {
              frappe.throw(
                "Net Pay of salary slip cannot be less than NGN 100"
              );
            }
          }
        );
      }
    );
  }
);

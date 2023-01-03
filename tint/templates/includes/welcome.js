// frappe.call({
//   method: "frappe.core.doctype.user.user.generate_keys",
//   args: {
//     user: 'Administrator',
//   },
//   callback: function (r) {
//     if (r.message) {
//       frappe.msgprint(__("Save API Secret: ") + r.message.api_secret);
//     }
//   },
// });

// check if customer site is present
// check if sub present and status, and card_token/txRef to confirm payment
// check create the user and redirect to login

// frappe.ready(function () {
//   fetch(
//     "http://test.local:8000/api/method/tint.tint.central.api.get_site_details",
//     {
//       headers: {
//         Authorization: `token ${api_key}`,
//       },
//     }
//   )
//     .then((r) => r.json())
//     .then((r) => {
//       console.log(r);
//     });
// frappe.ready(function () {
//   fetch(
//     "http://test.local:8000/api/method/tint.tint.central.api.get_site_details",
//     {
//       method: "POST",
//       headers: {
//         Authorization: "{{ auth }}",
//       },
//       body: JSON.stringify({
//         site: "{{ site }}",
//       }),
//     }
//   )
//     .then((r) => r.json())
//     .then((r) => {
//       console.log(r);
//     })
//     .catch((e) => {
//       console.log(e);
//     });

  // frappe.call({
  //   method: "login",
  //   args: {
  //     usr: "Administrator",
  //     pwd: "test",
  //     lead_email: "test@example.com",
  //   },
  //   callback: function (r) {
  //     // $(me).prop("disabled", false);
  //     console.log(r);
  //     if (r.exc) {
  //       alert("Error, please contact support@chimso.xyz");
  //     } else {
  //       console.log("Logged In");
  //       window.location.href = "desk";
  //     }
  //   },
  // });
// });


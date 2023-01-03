document
  .querySelector('[data-doctype="User"][data-name="Administrator"]')
  // .closest("div.list-row-container").style.display = "none";
console.log(
  'hola',
  document.querySelector('[data-doctype="User"][data-name="Administrator"]')
);
  frappe.require("/assets/tint/js/variables.js", () => {
  // To hide manager roles and Admin user in user sites
  const host = window.location.host;
  const route = frappe.get_route();
  console.log(
    manager_roles_map,
    route
  );

  if (centrals.some((url) => url !== host)) {
    console.log("Not central");
    // check if the current route is user's list
    const is_user_list_view =
      route.some((r) => /list/i.test(r)) && route.some((r) => /user/i.test(r));
    console.log("user view", is_user_list_view);
    // if (is_user_list_view) {
    Object.keys(manager_roles_map).forEach((role) => {
      const role_name = manager_roles_map[role].role;
      const user_el = document.querySelector(
        `[data-doctype="User"][data-name="${
          /admin/i.test(role_name) ? "Administrator" : role_name
        }"]`
      );
      console.log("user el", role_name, user_el);
      
      if (user_el) {
        const list_item = user_el.closest("div.list-row-container");
        // hide the list row
        list_item.style.display = "none !important";
      }
    });
    // document
    //   .querySelector('[data-doctype="User"][data-name="Administrator"]')
    //   .closest("div.list-row-container");
    // }
  }
});

/** @odoo-module **/

import { NavBar } from "@web/webclient/navbar/navbar";
import { patch } from "@web/core/utils/patch";

patch(NavBar.prototype, {
    onNavBarDropdownItemSelection(menu) {
        const xmlids = [
            "website.menu_website_preview",
            "website.menu_edit_menu",
            "website.menu_optimize_seo",
            "website.menu_ace_editor",
            "website.menu_page_properties",
            "website.custom_menu_edit_menu",
        ];
        if (xmlids.includes(menu.xmlid)) {
            $('[data-menu-xmlid="website.menu_edit_menu"]').parent().show();
            $('[data-menu-xmlid="website.menu_current_page"]').parent().show();
        } else {
            $('[data-menu-xmlid="website.menu_edit_menu"]').parent().hide();
            $('[data-menu-xmlid="website.menu_current_page"]').parent().hide();
        }
        return super.onNavBarDropdownItemSelection(menu);
    },
});

/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { ListRenderer } from "@web/views/list/list_renderer";
import { DashPager } from "./dash_pager";
import { useState } from "@odoo/owl";

patch(ListRenderer.prototype, {
    setup() {
        super.setup();
        this.pagerProps = this.env.config.pagerProps
            ? useState(this.env.config.pagerProps)
            : undefined;
    },
});

ListRenderer.components = {
    ...ListRenderer.components,
    DashPager,
};

/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { ActivityRenderer } from "@mail/views/web/activity/activity_renderer";
import { DashPager } from "./dash_pager";
import { useState } from "@odoo/owl";

patch(ActivityRenderer.prototype, {
    setup() {
        super.setup();
        this.pagerProps = this.env.config.pagerProps
            ? useState(this.env.config.pagerProps)
            : undefined;
    },
});

ActivityRenderer.components = {
    ...ActivityRenderer.components,
    DashPager,
};

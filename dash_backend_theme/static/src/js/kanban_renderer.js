/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { DashPager } from "./dash_pager";
import { useState } from "@odoo/owl";

patch(KanbanRenderer.prototype, {
    setup() {
        super.setup();
        this.pagerProps = this.env.config.pagerProps
            ? useState(this.env.config.pagerProps)
            : undefined;
    },
});

KanbanRenderer.components = {
    ...KanbanRenderer.components,
    DashPager,
};

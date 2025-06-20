/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { FormRenderer } from "@web/views/form/form_renderer";
import { ensureJQuery } from "@web/core/ensure_jquery";
import { onMounted, onWillStart, onWillUnmount } from "@odoo/owl";

patch(FormRenderer.prototype, {
    setup() {
        super.setup();
        this.mediaQuery = window.matchMedia("(min-width: 1600px)");
        onMounted(this.onMounted);
        onWillStart(this.onWillStart);
        onWillUnmount(this.onWillUnmount);
        window.addEventListener("resize", function () {
            const event = new Event("devicepixelratiochange");
            window.dispatchEvent(event);
        });
        const self = this;
        window.addEventListener("devicepixelratiochange", function (e) {
            self.handleMediaChange(self.mediaQuery);
        });
    },
    onMounted() {
        this.mediaQuery.addEventListener("change", this.handleMediaChange);
        this.handleMediaChange(this.mediaQuery);
    },
    async onWillStart() {
        await ensureJQuery();
    },
    onWillUnmount() {
        this.mediaQuery.removeEventListener("change", this.handleMediaChange);
    },
    handleMediaChange(e) {
        if ($(".tree_form_split_view").length == 0 && $(".modal-body").length == 0) {
            if (e.matches) {
                setTimeout(() => {
                    const currentWidth = $(".o_form_sheet_bg").width();
                    $(".o_control_panel").width(currentWidth + 66);
                    $(".o_content").css("background", "unset");
                }, 100);
            } else {
                $(".o_control_panel").css("width", "initial");
            }
        }
    },
});

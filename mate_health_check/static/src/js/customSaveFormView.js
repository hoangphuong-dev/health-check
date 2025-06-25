/** @odoo-module **/

import { registry } from "@web/core/registry";
import { FormController } from "@web/views/form/form_controller";
import { useService } from "@web/core/utils/hooks";

class CustomFormController extends FormController {
    setup() {
        super.setup();
        this.action = useService("action");
    }

    async save() {
        const res = await super.save();
        if (res) {
            this.action.doAction("mate_health_check.mate_health_check_package_action", {
                clearBreadcrumbs: true,
            });
        }
    }
}

registry.category("views").add("custom_form_save_handler", {
    ...registry.category("views").get("form"),
    Controller: CustomFormController,
});

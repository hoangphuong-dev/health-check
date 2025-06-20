/** @odoo-module **/
import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { ListController } from "@web/views/list/list_controller";
import { useService } from "@web/core/utils/hooks";


export const registryCustomHeaderButton = (jsClassName, buttonTemplate, callback) => {
    class ListControllerExtend extends ListController {
        setup() {
            super.setup();
            this.orm = useService("orm");
            this.action = useService("action");
        }
        // Override the _onButtonClicked method to handle custom button click
        action_upload_service() {
            // Call the action to open the upload service wizard
            callback.bind(this)();
        }
    }
    const component = {
        ...listView,
        Controller: ListControllerExtend,
        buttonTemplate: buttonTemplate
    }
    registry.category("views").add(jsClassName, component);
};

registryCustomHeaderButton("upload_package_header_button", "mate_hms_package.ListViewReconcile.Buttons", function () {
    this.orm.call("mate_hms.package", "action_import_package_excel", [], {}).then((result) => {
        this.action.doAction(result);
    });
});

registryCustomHeaderButton("upload_appointment_header_button", "mate_hms_appointment.ListViewReconcile.Buttons", function () {
    this.orm.call("mate_hms.appointment", "action_create_appointment_import_services_excel", [], {}).then((result) => {
        this.action.doAction(result);
    });
});


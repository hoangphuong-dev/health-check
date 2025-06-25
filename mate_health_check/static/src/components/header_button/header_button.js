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
        action_service() {
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

registryCustomHeaderButton("create_department_header_button", "hr.department.ListViewReconcile.Buttons", function () {
    this.orm.call("mate.create.department.wizard", "action_create_department", [], {}).then((result) => {
        this.action.doAction(result);
    });
});

registryCustomHeaderButton("create_package_header_button", "mate_health_check_package.ListViewReconcile.Buttons", function () {
    this.orm.call("create.package.wizard", "action_create_package", [], {}).then((result) => {
        this.action.doAction(result);
    });
});

registryCustomHeaderButton("create_group_sequence_header_button", "mate_health_check_group_sequence.ListViewReconcile.Buttons", function () {
    this.orm.call("create.group.sequence.wizard", "action_save_group_sequence", [], {}).then((result) => {
        this.action.doAction(result);
    });
});

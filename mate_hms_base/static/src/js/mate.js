odoo.define("mate_hms_base.mate", function (require) {
    "use strict";
    const rpc = require("web.rpc");
    const core = require("web.core");

    core.bus.on("web_client_ready", null, function () {
        // Get block_ui data from backend
        rpc.query({
            model: "res.company",
            method: "mate_get_blocking_data",
        }).then(function (block_data) {
            // UI name
            if (block_data.name && block_data.name !== "False") {
                const block_ui = $('<div class="mate-block_ui hidden"/>');
                $("body").append(block_ui);
                block_ui.html(block_data.name);
                block_ui.show();
            }
        });
    });
});

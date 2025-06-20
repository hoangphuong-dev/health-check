/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { onWillUpdateProps } from "@odoo/owl";
import { X2ManyField } from "@web/views/fields/x2many/x2many_field";
import { DynamicGroupList } from "@web/model/relational_model/dynamic_group_list";
import { StaticList } from "@web/model/relational_model/static_list";



patch(X2ManyField.prototype,  {
    async setup() {
        
        onWillUpdateProps((props) => {
            if (this.props.record.data[this.props.name]  !== props.record.data[props.name]) {
                this.onRecordChange();
            }               
        });
        super.setup();
        
        await this.onRecordChange();

    },
    createGroupBy: function () {
        this.list._config.orderBy = this.props.context.orderBy.map((order) => {
            const data = order.split(" ");
            return {
                name: data[0],
                asc: data[1] === "asc",
            }
        })
    },
    onRecordChange() {
        if (this.props.context.groupBy) {
            return new Promise((resolve) => {
                if (this.time) {
                    clearTimeout(this.time);
                }
                this.time = setTimeout(async () => {
                    try {
                        this.list._config.groupBy = [this.props.context.groupBy];
                        this.list._config.domain = this.props.context.domain_key ? [[this.props.context.domain_key, '=', this.env.model.config.resId]] : [];
                        if (this.props.context.groupDomain) {
                            this.list._config.domain = this.props.context.groupDomain;
                        }
                        const data = await this.list.model.keepLast.add(this.list.model._loadGroupedList(this.list._config));
                        const newList = new DynamicGroupList(this.env.model, this.list._config, data);
                        if (this.list instanceof  StaticList) {
                            this.staticList = this.list;
                        }
                        let self = this;
                        Object.assign(newList, {
                            _unknownRecordCommands: this.list._unknownRecordCommands,
                            _abandonRecords: function (records, {force}={}) {
                                self.onRecordChange();
                            },
                            extendRecord: this.list.extendRecord,
                            _createNewRecordDatapoint: this.list._createNewRecordDatapoint,
                            _extendedRecords: this.list._extendedRecords,
                            _parent: this.list._parent,
                            _createRecordDatapoint: this.list._createRecordDatapoint,
                            addNewRecord : this.list.addNewRecord,
                            _cache: this.list._cache,
                            _addRecord : this.list._addRecord,
                            currentIds: this.list.currentIds,
                            _updateContext: this.list._updateContext,
                        });
                        this.props.record.data[this.props.name] = newList;
                    } finally {
                        resolve();
                    }
                })
            });
        }
    },

});

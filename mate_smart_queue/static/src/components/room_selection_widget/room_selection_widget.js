/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useState, onWillStart, onWillUpdateProps, Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class RoomSelectionWidget extends Component {
    static template = "mate_smart_queue.RoomSelectionWidget";
    static props = {
        ...standardFieldProps,
    };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");

        // Initialize state with proper value handling
        const currentValue = this.props.record.data.selected_room_id;
        this.state = useState({
            rooms: [],
            selectedRoomId: Array.isArray(currentValue) ? currentValue[0] : currentValue || false,
            currentRoomId: this.props.record.data.current_room_id?.[0] || false,
            isLoading: false,
        });

        onWillStart(async () => {
            await this.loadRooms();
        });

        // Handle props updates
        onWillUpdateProps((nextProps) => {
            const newValue = nextProps.record.data.selected_room_id;
            const newSelectedId = Array.isArray(newValue) ? newValue[0] : newValue || false;
            if (newSelectedId !== this.state.selectedRoomId) {
                this.state.selectedRoomId = newSelectedId;
            }
        });
    }

    async loadRooms() {
        const serviceId = this.props.record.data.service_id?.[0];
        if (!serviceId) {
            this.state.rooms = [];
            return;
        }

        this.state.isLoading = true;

        try {
            const rooms = await this.orm.searchRead(
                "hr.department",
                [
                    ["service_id", "=", serviceId],
                    ["state", "=", "open"]
                ],
                ["name", "location", "capacity", "queue_length", "estimated_wait_time"],
                { order: "name" }
            );

            const roomsWithCount = await Promise.all(
                rooms.map(async (room) => {
                    const waitingCount = await this.orm.searchCount(
                        "mate.queue.token",
                        [
                            ["room_id", "=", room.id],
                            ["state", "=", "waiting"]
                        ]
                    );

                    return {
                        ...room,
                        waiting_count: waitingCount,
                        is_current: room.id === this.state.currentRoomId,
                    };
                })
            );

            const processedRooms = roomsWithCount.map(room => {
                const waitTime = room.estimated_wait_time || 0;

                let waitColor = "success";
                if (waitTime > 30) {
                    waitColor = "danger";
                } else if (waitTime > 20) {
                    waitColor = "warning";
                }

                return {
                    ...room,
                    wait_color: waitColor,
                    wait_time_text: `${Math.round(waitTime)} phút`,
                    location: room.location || `Tầng 1, Phòng ${room.name.slice(-3) || room.id}`,
                };
            });

            if (processedRooms.length > 0) {
                const recommendedRoom = processedRooms.reduce((prev, current) =>
                    (current.waiting_count < prev.waiting_count) ? current : prev
                );
                recommendedRoom.is_recommended = true;
            }

            this.state.rooms = processedRooms;
        } catch (error) {
            console.error("Error loading rooms:", error);
            this.notification.add(_t("Lỗi khi tải danh sách phòng"), {
                type: "danger",
            });
        } finally {
            this.state.isLoading = false;
        }
    }

    selectRoom(roomId) {
        if (!roomId || roomId <= 0) {
            console.warn("Invalid room ID:", roomId);
            return;
        }

        this.state.selectedRoomId = roomId;
        try {
            // Find the room to get its name
            const selectedRoom = this.state.rooms.find(room => room.id === roomId);
            if (selectedRoom) {
                this.props.record.update({
                    selected_room_id: [roomId, selectedRoom.name]
                });
            }
        } catch (error) {
            // Rollback state if update failed
            this.state.selectedRoomId = this.props.record.data.selected_room_id;
        }
    }

    getRoomClasses(room) {
        const classes = ["room-card"];
        if (room.id === this.state.selectedRoomId) {
            classes.push("selected");
        }
        return classes.join(" ");
    }

    roomCurrent(room) {
        if (room.is_current) {
            return "Phòng hiện tại"
        }
        return "";
    }

    getServiceRoom() {
        const serviceId = this.props.record.data.service_id;
        return Array.isArray(serviceId) ? serviceId[1] : '';
    }
}

// Register the field widget properly
registry.category("fields").add("room_selection_widget", {
    component: RoomSelectionWidget,
    displayName: _t("Room Selection"),
    supportedTypes: ["many2one"],
    extractProps: ({ attrs }) => ({
        options: attrs.options || {},
    }),
});
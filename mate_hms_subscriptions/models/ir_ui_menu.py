from odoo import api, models


class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    @api.model
    def hide_menus_for_subscription_manager(self, menu_ids=None, group_id=None):
        """
        Ẩn các menu không liên quan cho Subscription Package Manager
        """
        # Danh sách ID của menu cho phép
        allowed_menu_xmlids = [
            'mate_hms.menu_hms',
            'mate_hms.action_menu_patient',
            'mate_hms.action_main_menu_appointmnet_opd',
            'mate_hms_subscriptions.action_main_menu_subscriptions',
            'mate_hms_subscriptions.menu_subscriptions',
            'mate_hms_subscriptions.menu_package'
        ]

        # Lấy các menu từ XML ID
        allowed_menu_ids = []
        for xml_id in allowed_menu_xmlids:
            menu = self.env.ref(xml_id, raise_if_not_found=False)
            if menu:
                allowed_menu_ids.append(menu.id)
                # Thêm menu con
                child_menus = self.search([('parent_id', '=', menu.id)])
                allowed_menu_ids.extend(child_menus.ids)

        # Tìm các menu khác và ẩn chúng
        if group_id:
            group = self.env['res.groups'].browse(group_id)
            # Lấy tất cả menu có thể nhìn thấy
            all_menu_ids = self.search([]).ids

            # Menu không được phép
            hide_menu_ids = list(set(all_menu_ids) - set(allowed_menu_ids))

            # Xóa menu không được phép khỏi nhóm quyền
            for menu_id in hide_menu_ids:
                menu = self.browse(menu_id)
                if group in menu.groups_id:
                    menu.write({'groups_id': [(3, group_id)]})

        return True

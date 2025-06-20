{
    'name': "Smart Queue",
    'summary': """
        Hệ thống quản lý hàng đợi khám sức khỏe thông minh dựa trên token based
    """,
    # 'description': """
    #     Module này triển khai hệ thống quản lý hàng đợi thông minh cho cơ sở y tế, giúp:
    #     - Phân phối bệnh nhân hiệu quả giữa các phòng
    #     - Giảm thời gian chờ đợi
    #     - Ưu tiên các trường hợp khẩn cấp
    # """,
    'author': "Mate Technology JSC",
    'website': "https://www.yourcompany.com",
    'category': 'Healthcare',
    'version': '18.0.1.0.0',
    'depends': ['mate_health_check'],
    'data': [
        'security/ir.model.access.csv',

        # views
        'data/coordination_actions.xml',

        # 2. Các views và biểu mẫu (để model được tạo ra)
        'views/patient_view.xml',
        'views/log_coordination_views.xml',
        'views/queue_views.xml',
        'views/queue_room_selection_wizard_views.xml',

        # data seeding
        'data/demo_data.xml',
    ],
    'qweb': [
    ],
    'assets': {
        'web.assets_backend': [
            'mate_smart_queue/static/src/xml/kanban_buttons.xml',
            'mate_smart_queue/static/src/js/queue_coordination_kanban.js',
            'mate_smart_queue/static/src/scss/queue_coordination.scss',

            'mate_smart_queue/static/src/components/room_selection_widget/room_selection_widget.js',
            'mate_smart_queue/static/src/components/room_selection_widget/room_selection_widget.xml',
            'mate_smart_queue/static/src/components/room_selection_widget/room_selection_widget.scss',
        ],
    },
    'application': True,
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'images': [
        'static/description/banner.png',
    ],
}

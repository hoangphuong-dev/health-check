{
    'name': 'Base - Hospital Management System ( HMS by Mate )',
    'summary': 'Hospital Management System Base for further flows',
    'description': """
        Hospital Management System for managing Hospital and medical facilities flows
        Medical Flows Mate HMS

        This module helps you to manage your hospitals and clinics which includes managing
        Patient details, Doctor details, Prescriptions, Treatments, Appointments with concerned doctors,
        Invoices for the patients. You can also define the medical alerts of a patient and get warining in appointment,treatments and prescriptions. It includes all the basic features required in Health Care industry.

        healthcare services healthcare administration healthcare management health department
        hospital management information system hospital management odoo hms odoo medical alert

        Ce module vous aide à gérer vos hôpitaux et vos cliniques, ce qui inclut la gestion
         Détails du patient, détails du médecin, prescriptions, traitements, rendez-vous avec les médecins concernés,
         Factures pour les patients. Il comprend toutes les fonctionnalités de base requises dans l'industrie des soins de santé.

        services de santé administration des soins de santé gestion des soins de santé département de la santé
         système d'information de gestion hospitalière gestion hospitalière odoo hms odoo

        Système de gestion hospitalière pour la gestion des flux d'hôpitaux et d'installations médicales
         Flux médicaux Mate HMS

        نظام إدارة المستشفيات لإدارة تدفقات المستشفيات والمرافق الطبية
        التدفقات الطبية Mate HMS

        هذه الوحدة تساعدك على إدارة مستشفيات وعياداتك التي تشمل الإدارة
        تفاصيل المريض ، تفاصيل الطبيب ، الوصفات الطبية ، العلاجات ، المواعيد مع الأطباء المعنيين ،
        ويشمل جميع الميزات الأساسية المطلوبة في صناعة الرعاية الصحية.فواتير للمرضى.

        خدمات الرعاية الصحية إدارة الرعاية الصحية إدارة الصحة الصحية
        إدارة مستشفى إدارة معلومات نظام إدارة

        Hospital Management System zur Verwaltung von Krankenhaus- und medizinischen Abläufen
         Medizinische Strömungen Mate HMS

        Dieses Modul hilft Ihnen bei der Verwaltung Ihrer Krankenhäuser und Kliniken, einschließlich der Verwaltung
         Angaben zum Arzt, Angaben zum Arzt, Rezepte, Behandlungen, Termine mit betroffenen Ärzten,
         Rechnungen für die Patienten. Es enthält alle grundlegenden Funktionen, die in der Gesundheitsbranche erforderlich sind.

        Gesundheitsdienste Gesundheitsverwaltung Gesundheitsmanagement Gesundheitsabteilung
         Krankenhaus-Management-Informationssystem Krankenhaus-Management odoo hms odoo


        Sistema de gestión hospitalaria para la gestión de flujos hospitalarios e instalaciones médicas.
         Flujos medicos Mate HMS

        This module helps you to manage your hospitals and clinics which includes managing
        Patient details, Doctor details, Prescriptions, Treatments, Appointments with concerned doctors,
        Invoices for the patients. It includes all the basic features required in Health Care industry.

        servicios de salud administración de la salud administración de la salud departamento de salud
         gestión hospitalaria sistema de información gestión hospitalaria odoo hms odoo
    """,
    'version': "18.0.1.0.0",
    'category': 'Medical',
    'author': 'Mate Technology JSC',
    'support': 'info@mate.com.vn',
    'website': 'https://www.mate.com.vn',
    'license': 'OPL-1',
    'depends': ['account', 'stock', 'hr', 'product_expiry'],
    'data': [
        'security/mate_security.xml',
        'security/ir.model.access.csv',

        'report/mate_paper_format.xml',
        'report/mate_report_layout.xml',
        'report/mate_report_invoice.xml',

        'data/mate_sequence.xml',
        'data/mate_mail_template.xml',
        'data/mate_company_data.xml',

        'views/mate_hms_base_views.xml',
        'views/mate_patient_view.xml',
        'views/mate_physician_view.xml',
        'views/mate_product_view.xml',
        'views/mate_drug_view.xml',
        'views/mate_account_view.xml',
        'views/mate_res_config_settings.xml',
        'views/mate_stock_view.xml',
        'views/mate_res_country_view.xml',
        'views/mate_menu_item.xml',
    ],
    'demo': [
        'demo/mate_company_demo.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'mate_hms_base/static/src/scss/report.scss'
        ],
        "web.assets_common": [
            "mate_hms_base/static/src/js/mate.js",
            'mate_hms_base/static/src/scss/mate.scss',
        ],
    },
    'images': [
        'static/description/hms_mate_cover.jpg',
    ],
    'installable': True,
    'application': True,
    'sequence': 1,
    'price': 36,
    'currency': 'USD',
    'old_technical_name': 'mate_hms_base',
}

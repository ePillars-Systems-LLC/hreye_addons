
{
    "name": "Update Oddo Background Image",
    "summary": "This module allows the odoo admin user to update odoo15 Image to odoo17.",
    "version": "17.1",
    "description": """
        This module allows the odoo admin user to update odoo15 Image to odoo17.      
    """,    
    "author": "ePIllars Systems LLC",
    "maintainer": "ePIllars Systems LLC",
    "license" :  "Other proprietary",
    "website": "https://www.epillars.com",
    "images": ["images/odoo_bg_updation.png"],
    "category": "Extra Tools",
    "depends": [
        "web",
        "base_setup",
        "web_editor",
    ],
    "data": [
        "templates/webclient.xml",
        "views/res_config_settings.xml",
    ],
    "assets": {
        "web._assets_primary_variables": [
            ("prepend", "odoo_bg_updation/static/src/scss/colors.scss"),
            (
                "before", 
                "odoo_bg_updation/static/src/scss/colors.scss", 
                "odoo_bg_updation/static/src/scss/colors_light.scss"
            ),
        ],
        'web.assets_web_dark': [
            (
                'after', 
                'odoo_bg_updation/static/src/scss/colors.scss', 
                'odoo_bg_updation/static/src/scss/colors_dark.scss'
            ),
        ],
        "web.assets_backend": [
            "/odoo_bg_updation/static/src/css/*.*",
            "/odoo_bg_updation/static/src/js/*.*",
        ],
    },
    "installable": True,
    "application": True,
}

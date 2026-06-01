{
    'name': 'VLA Tokens',
    'version': '18.0.1.0.0',
    'summary': 'B2C/B2B assessment token wallet with duration-based balances and course invite deduction.',
    'description': """
VLA Tokens
==========

Adds duration-based token handling for Achev/VLA assessments.

Main flow supported now:
- Configure the main saleable products as 30-minute and 60-minute courses.
- Configure product variants as token quantities: 1, 50, and 100.
- 1-token variants are B2C and create customer registration URLs that are emailed after payment.
- 50/100-token variants are B2B and credit company token inventory by duration.
- Course invites deduct one token per invite recipient from the matching 30/60 minute company wallet.
- Wallet balances, B2C URLs, and ledger records are visible on the contact form.
""",
    'author': 'Maria',
    'license': 'LGPL-3',
    'category': 'Sales',
    'depends': [
        'base',
        'contacts',
        'product',
        'sale_management',
        'account',
        'mail',
        'website',
        'website_sale',
        'website_slides',
        'website_sale_slides',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/mail_template_data.xml',
        'data/ir_cron_data.xml',
        'views/product_product_views.xml',
        'views/website_sale_templates.xml',
        'views/res_partner_views.xml',
        'views/vla_token_wallet_line_views.xml',
        'views/vla_assessment_token_views.xml',
        'views/sale_invoice_partner_domain_views.xml',
    ],

    'assets': {
        'web.assets_frontend': [
            'vla_tokens/static/src/js/vla_variant_note.js',
        ],
    },
    'installable': True,
    'application': False,
}

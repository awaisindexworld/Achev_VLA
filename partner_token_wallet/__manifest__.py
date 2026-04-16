{
    'name': 'Partner Token Wallet',
    'version': '18.0.1.0.0',
    'summary': 'Credits paid token purchases to contacts and tracks token balances by duration.',
    'description': """
Partner Token Wallet
====================

This module adds a token wallet on contacts/customers.

Main features:
- Configure products as token bundle / course selector / final token products.
- Credit tokens to the customer only when the customer invoice is fully paid.
- Track separate balances for 15 / 30 / 60 minute tokens.
- Keep a full token ledger on the contact form.
- Provide reusable partner methods to consume tokens from custom invite flows.
""",
    'author': 'OpenAI',
    'license': 'LGPL-3',
    'category': 'Sales',
    'depends': ['base', 'contacts', 'product', 'sale_management', 'account', 'website_sale_slides'],
    'data': [
        'security/ir.model.access.csv',
        'views/product_template_views.xml',
        'views/res_partner_views.xml',
        'views/token_wallet_line_views.xml',
    ],
    'installable': True,
    'application': False,
}

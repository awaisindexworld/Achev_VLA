# Partner Token Wallet

This Odoo 18 custom module adds a token wallet to contacts/customers.

## What it does

- Adds token configuration fields on products.
- Credits tokens only when a customer invoice is fully paid.
- Tracks separate balances for 15 / 30 / 60 minute tokens.
- Shows a token wallet tab on the contact form.
- Keeps a full token ledger.
- Exposes reusable partner methods for custom invite deduction.

## Supported product setup

### Option 1: Final Token Product
Use one product that already defines both:
- token quantity
- token time type

Example:
- 50 tokens / 30 minutes

### Option 2: Bundle + Course Type product
Use two products in the same order/invoice:
- one Bundle product with token quantity only, like 50 or 100
- one Course Token Type product with 15 / 30 / 60 minutes only

This module credits tokens automatically when there is exactly:
- 1 bundle line, and
- 1 course token type line

on the paid customer invoice.

## Contact fields added

- 15 Min Tokens
- 30 Min Tokens
- 60 Min Tokens
- Total Available
- Token history / ledger

## Invite deduction hook

This part depends on your existing course/invite code.
The module already provides these reusable methods on `res.partner`:

- `partner.token_wallet_consume('15', quantity=1, source_record=record, note='...')`
- `partner.token_wallet_consume_from_duration(15, quantity=1, source_record=record, note='...')`
- `self.env['res.partner'].token_wallet_consume_from_user(user, 15, quantity=1, source_record=record, note='...')`

### Example business rule

- 15-minute course invite -> consume 1 token from 15-minute balance
- 30-minute course invite -> consume 1 token from 30-minute balance
- 60-minute course invite -> consume 1 token from 60-minute balance

## Important note

I did **not** hard-wire the invite deduction to a specific course model because your exact invite model and send method were not provided here.
That final hook should be added where your invite is actually created/sent.

## Install

- Copy module into your custom addons path.
- Update apps list.
- Install **Partner Token Wallet**.

## Recommended product configuration for your case

From your screenshots, the most likely setup is:

- `50 Tokens | 15% off` -> Token Wallet Role = `Token Bundle`, Token Quantity = `50`
- `100 Tokens | 25% off` -> Token Wallet Role = `Token Bundle`, Token Quantity = `100`
- `15 minutes: Quick assessment` -> Token Wallet Role = `Course Token Type`, Token Time Type = `15`
- `30 minutes: Intermediate assessment` -> Token Wallet Role = `Course Token Type`, Token Time Type = `30`
- `60 minutes: Advance assessment` -> Token Wallet Role = `Course Token Type`, Token Time Type = `60`

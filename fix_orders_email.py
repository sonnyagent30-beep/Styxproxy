import sys

path = 'backend/app/routers/orders.py'
content = open(path, 'r', newline='').read()

# Fix: Wrap send_new_order_notification in try/except to prevent order creation failure
old = '    # Send admin notification email\n    if order.status == "pending":\n        await send_new_order_notification(\n            order_id=order_id,\n            customer_phone=customer.phone,\n            plan_code=body.plan_code,\n            amount=total_amount,\n            currency="NGN",\n        )'

new = '    # Send admin notification email\n    if order.status == "pending":\n        try:\n            await send_new_order_notification(\n                order_id=order_id,\n                customer_phone=customer.phone,\n                plan_code=body.plan_code,\n                amount=total_amount,\n                currency="NGN",\n            )\n        except Exception as e:\n            logger.warning(f\'Failed to send new order notification: {e}\')'

if old in content:
    content = content.replace(old, new)
    open(path, 'w', newline='').write(content)
    print('✅ orders.py: send_new_order_notification wrapped in try/except')
else:
    print('Pattern not found')
    sys.exit(1)

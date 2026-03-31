# Payment Approval + QR Code - TODO

Approved plan.

**Step 1** (current): payment/models.py - add payment_proof FileField, qr_code ImageField

**Step 2**: payment/views.py - screenshot display, on approve generate QR (reg ID, name, activity), save image

**Step 3**: templates/payment/status.html - screenshot preview, QR show/download, approve button

**Step 4**: templates/events/event_dashboard.html - add "View Payments" button

**Step 5**: templates/events/manage_activities.html - "Payments" column

**Step 6**: Migrate + pip pillow qrcode

**Next**: Edit payment/models.py


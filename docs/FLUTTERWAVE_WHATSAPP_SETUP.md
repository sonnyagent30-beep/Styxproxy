# Bunche — Flutterwave & WhatsApp Setup Guide
*Step-by-step for the two integrations that make this work*

---

## Part 1: Flutterwave Setup

### 1.1 Create Flutterwave Account

1. Go to **rave.flutterwave.com**
2. **Get Started** → Sign Up
3. Choose **Business** account
4. Fill in: Business name, email, phone, business type

### 1.2 Complete Verification (KYC)

**For Sole Proprietorship:**
- BVN (Bank Verification Number)
- NIN or passport
- Utility bill or bank statement

**Timeline:** 1–5 business days.

### 1.3 Get Your API Keys

1. Dashboard → **Settings** → **API Keys**
2. Save all three: **Public Key**, **Secret Key**, **Encryption Key**
3. You cannot see Secret Key again after leaving — save it now

### 1.4 Set Up Webhook URL

1. Dashboard → **Settings** → **Webhooks**
2. Add: `https://n8n.yourdomain.com/webhook/flutterwave`
3. Select events:
   - ✅ `charge.completed`
   - ✅ `charge.failed`
   - ✅ `refund.initiated`
   - ✅ `refund.completed`
4. Save

### 1.5 Test Webhook

1. Dashboard → Settings → Webhooks → **Send Test**
2. Select `charge.completed` → Send
3. Check n8n Payment Confirmation workflow — test should appear

---

## Part 2: WhatsApp Business API Setup

### Option A: WhatsApp Business API (Direct)

**Apply:** business.whatsapp.com → Get Started
- Takes 1–4 weeks for approval
- Need: Meta Business Account, dedicated phone number, Privacy Policy URL

### Option B: Twilio WhatsApp (Easier Alternative)

1. Sign up at **twilio.com/whatsapp**
2. Request WhatsApp sandbox (fastest approval)
3. Get a Twilio WhatsApp number
4. In n8n: use Twilio webhook trigger instead of WhatsApp Cloud API

**Pros:** Faster approval, easier integration
**Cons:** Slightly more expensive (~$0.05/message outbound)

### WhatsApp API Configuration

Once you have API access:
1. Get **Phone Number ID** from Meta Business Console
2. Get **Access Token**
3. Set Webhook URL: `https://n8n.yourdomain.com/webhook/whatsapp-incoming`
4. Set Verify Token: any random string
5. Subscribe to: `message_received`

---

## Part 3: Connecting Everything

### Nginx Configuration for Webhooks

Both Flutterwave and WhatsApp need to reach your n8n webhooks:

```nginx
server {
    listen 80;
    server_name n8n.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:5678;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_buffering off;
    }
}
```

```bash
# Enable and get SSL
ln -s /etc/nginx/sites-available/n8n /etc/nginx/sites-enabled/
nginx -t
certbot --nginx -d n8n.yourdomain.com
```

### Webhook URLs Summary

| Service | Webhook URL |
|---------|------------|
| Flutterwave | `https://n8n.yourdomain.com/webhook/flutterwave` |
| WhatsApp | `https://n8n.yourdomain.com/webhook/whatsapp-incoming` |

---

## Checklist Before Launch

- [ ] Flutterwave account verified
- [ ] Flutterwave API keys saved in n8n
- [ ] Flutterwave webhook URL set and tested
- [ ] WhatsApp Business API approved (or Twilio WhatsApp set up)
- [ ] WhatsApp Access Token saved in n8n
- [ ] WhatsApp webhook URL set and verified
- [ ] Nginx configured with SSL
- [ ] n8n accessible at `https://n8n.yourdomain.com`
- [ ] All 4 workflows are ACTIVE
- [ ] Test payment + delivery completed end-to-end
- [ ] Legal pages (ToS, Privacy Policy, AUP) are live

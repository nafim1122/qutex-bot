# 🚀 Vercel Deployment Guide

## USD/BDT Trading Bot on Vercel

This guide walks you through deploying the USD/BDT Trading Bot to Vercel for live dashboard and API access.

### Prerequisites

1. **Vercel Account** - Sign up at [vercel.com](https://vercel.com)
2. **GitHub Account** - Already configured with your repository
3. **GitHub Repository** - Your code is at `https://github.com/nafim1122/qutex-bot.git`

---

## Step 1: Connect GitHub to Vercel

1. Go to [vercel.com](https://vercel.com)
2. Click "Sign Up" → Choose "Continue with GitHub"
3. Authorize Vercel to access your GitHub account
4. Click "Create Team" or skip to continue

---

## Step 2: Import Your Repository

1. Click **"Add New Project"** on the Vercel dashboard
2. Click **"Import Project"**
3. Paste your repository URL: `https://github.com/nafim1122/qutex-bot.git`
4. Click **"Continue"**

---

## Step 3: Configure Project Settings

1. **Project Name**: `qutex-bot` (or your preferred name)
2. **Framework Preset**: Select **"Other"** (Python project)
3. **Root Directory**: Leave as default
4. **Environment Variables** (optional):
   ```
   PYTHONUNBUFFERED=1
   PYTHONDONTWRITEBYTECODE=1
   ```

---

## Step 4: Deploy

1. Click **"Deploy"** button
2. Vercel will:
   - Install dependencies from `requirements.txt`
   - Build the project
   - Deploy to production
3. Wait for deployment to complete (usually 2-3 minutes)

---

## Step 5: Access Your Live Dashboard

Once deployed, you'll get:

```
🌐 https://qutex-bot-<username>.vercel.app/
```

**Available Endpoints:**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API status & endpoints |
| `/health` | GET | Health check |
| `/price` | GET | Current USD/BDT price |
| `/stats` | GET | Trading statistics |
| `/trade` | POST | Execute trade |

---

## Step 6: Live Dashboard

Your dashboard is automatically available at:
```
https://qutex-bot-<username>.vercel.app
```

**Features:**
- 📊 Real-time price display
- 💰 Account balance and P&L
- 📈 Trading statistics
- 🎯 Latest signal generation
- ✅ Model performance metrics
- 🎮 Start/Stop trading controls

---

## Step 7: Continuous Deployment

From now on:
- Any push to `main` branch → **Automatic deployment**
- Vercel will rebuild and redeploy in ~2-3 minutes
- No manual deployment needed

**To make changes:**
```bash
# 1. Make code changes locally
git add .
git commit -m "Update description"

# 2. Push to GitHub
git push origin main

# 3. Vercel automatically deploys
```

---

## API Usage Examples

### Get Current Price
```bash
curl https://qutex-bot-<username>.vercel.app/price
```

Response:
```json
{
  "status": "success",
  "pair": "USD/BDT",
  "price": 110.50,
  "timestamp": "2026-03-15T10:30:45"
}
```

### Get Trading Statistics
```bash
curl https://qutex-bot-<username>.vercel.app/stats
```

Response:
```json
{
  "status": "success",
  "account": {
    "balance": 10000.00,
    "pnl": 450.00,
    "pnl_percent": 4.5
  },
  "trades": {
    "total": 12,
    "wins": 8,
    "losses": 4,
    "win_rate": 66.7
  },
  "model": {
    "lstm_accuracy": 99.4,
    "confirmation_rate": 87.3
  }
}
```

### Execute Trade (POST)
```bash
curl -X POST https://qutex-bot-<username>.vercel.app/trade \
  -H "Content-Type: application/json" \
  -d '{"direction": "BUY"}'
```

Response:
```json
{
  "status": "success",
  "trade": {
    "id": 1001,
    "direction": "BUY",
    "entry": 110.50,
    "stop_loss": 110.40,
    "take_profit": 110.65,
    "status": "OPEN"
  }
}
```

---

## Monitoring & Analytics

Vercel provides built-in monitoring:

1. **Deployments Tab** - View all deployments
2. **Analytics Tab** - Monitor API usage
3. **Logs Tab** - Check application logs
4. **Settings Tab** - Configure domains & environment

---

## Troubleshooting

### Deployment Failed
- Check logs in Vercel dashboard
- Ensure `requirements.txt` has all dependencies
- Verify Python 3.11+ is compatible

### API Not Working
- Check if deployment succeeded
- Verify endpoint URLs are correct
- Check browser console for errors

### Performance Issues
- Monitor API analytics in Vercel
- Check function execution time
- Consider upgrading Vercel plan

---

## Domain Configuration (Optional)

To use a custom domain:

1. Go to Vercel Project Settings
2. Click "Domains"
3. Enter your custom domain
4. Update DNS records as instructed

Example: `trading-bot.yourdomain.com`

---

## Environment Variables (Optional)

Add environment variables for:
- API keys (if using external APIs)
- Trading configurations
- Model parameters

1. Go to Project Settings → Environment Variables
2. Click "Add"
3. Enter key and value
4. Click "Save"
5. Redeploy project

---

## Scheduled Tasks (Advanced)

To run trading bot on a schedule:

1. Use Vercel Cron Jobs (Pro plan)
2. Or use external service like AWS Lambda
3. Or use GitHub Actions to trigger trades

---

## Security Best Practices

⚠️ **Important:**
- ✅ Use environment variables for secrets
- ✅ Enable Vercel authentication
- ✅ Use HTTPS only (Vercel provides automatic SSL)
- ✅ Validate all API requests
- ✅ Rate limit API endpoints
- ✅ Monitor for suspicious activity

---

## Scaling Considerations

- **Free Plan**: Suitable for demo/testing
- **Pro Plan**: For production trading
- **Enterprise**: For high-frequency trading

---

## Next Steps

1. ✅ Deploy to Vercel
2. ✅ Test API endpoints
3. ✅ Access live dashboard
4. ✅ Monitor trading activity
5. ✅ Set up custom domain (optional)
6. ✅ Configure environment variables
7. ✅ Enable continuous deployment

---

## Support

**Vercel Documentation:** https://vercel.com/docs
**GitHub Issues:** https://github.com/nafim1122/qutex-bot/issues
**Email:** nafim1122@gmail.com

---

## Quick Links

- 📊 [Dashboard](https://qutex-bot-username.vercel.app)
- 🐙 [GitHub Repository](https://github.com/nafim1122/qutex-bot)
- 🔗 [Vercel Project](https://vercel.com/dashboard)
- 📚 [Main README](../README.md)

---

**Status:** ✅ Production Ready | **Version:** 1.0.0 | **Last Updated:** March 15, 2026

🎉 **Your trading bot is now live on Vercel!**

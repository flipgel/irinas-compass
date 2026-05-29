# Deploy Irina's Compass to Streamlit Cloud (Free)

This guide walks you through hosting Irina's Compass online so anyone can use it from a browser — no installation needed.

---

## Step 1: Create a GitHub Account

If you don't have one, sign up at [github.com](https://github.com) (free).

## Step 2: Create a New Repository

1. Go to [github.com/new](https://github.com/new)
2. **Repository name:** `irinas-compass`
3. Set it to **Public** (required for free Streamlit Cloud)
4. Click **Create repository**

## Step 3: Push the Code

From this machine, run these commands (replace `YOUR_USERNAME` with your GitHub username):

```bash
cd /home/k56/Desktop/IrinasCompass
git remote add origin https://github.com/YOUR_USERNAME/irinas-compass.git
git branch -M main
git push -u origin main
```

You'll be prompted for your GitHub username and password (or personal access token).

> **Tip:** If you have 2FA enabled, use a [personal access token](https://github.com/settings/tokens) instead of your password.

## Step 4: Deploy on Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Sign in with your **GitHub** account
3. Click **"New app"**
4. Select:
   - **Repository:** `YOUR_USERNAME/irinas-compass`
   - **Branch:** `main`
   - **Main file path:** `app.py`
5. Click **Deploy**

Streamlit Cloud will build and deploy your app. In 2–3 minutes, you'll get a URL like:

```
https://irinas-compass-abc123.streamlit.app
```

## Step 5: Share the Link

Send the URL to Irina. She can:
- Open it on her phone, tablet, or laptop
- Bookmark it
- Use it from anywhere with internet

## Updating the App

Whenever you make changes locally:

```bash
cd /home/k56/Desktop/IrinasCompass
git add .
git commit -m "Update description"
git push origin main
```

Streamlit Cloud will **auto-redeploy** within minutes.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Module not found" on deploy | Make sure `requirements.txt` is committed and pushed |
| App says "Please wait" forever | Check Streamlit Cloud logs (Manage App → Logs) |
| Git push fails | Make sure you're using a personal access token, not password |
| 404 on companyinfo.ge API | The API is occasionally rate-limited; wait a minute and retry |

---

**Cost:** $0. Streamlit Cloud free tier includes 1 GB RAM and enough compute for this app.

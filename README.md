# Reddit News Bot

A fully automated Python bot that fetches news from RSS feeds and posts to a subreddit every 30 minutes.

## Features
- **Automated Posting**: Posts exactly 2 times per hour.
- **Duplicate Prevention**: Tracks posted URLs to avoid reposts.
- **Auto-Recovery**: Handles errors and retries automatically.
- **Free Hosting Ready**: Designed for Render, Railway, or Fly.io free tiers.

## Prerequisites
- Python 3.10+
- A Reddit account
- A Reddit App (Script type)

## Setup Instructions

### 1. Create Reddit App
1. Go to [https://www.reddit.com/prefs/apps](https://www.reddit.com/prefs/apps).
2. Click **"create another app..."**.
3. Select **"script"**.
4. Fill in:
   - **name**: `news-bot` (or anything you like)
   - **redirect uri**: `http://localhost:8080` (doesn't matter for script apps)
5. Click **"create app"**.
6. Note down the **Client ID** (under the name) and **Client Secret**.

### 2. Local Testing
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Set environment variables (Windows PowerShell):
   ```powershell
   $env:REDDIT_CLIENT_ID="your_client_id"
   $env:REDDIT_CLIENT_SECRET="your_client_secret"
   $env:REDDIT_USERNAME="your_username"
   $env:REDDIT_PASSWORD="your_password"
   $env:SUBREDDIT_NAME="your_subreddit"
   $env:REDDIT_USER_AGENT="python:news-bot:v1.0 (by /u/your_username)"
   ```
3. Run the bot:
   ```bash
   python bot.py
   ```

## Deployment on Render (Free Tier)

1. **Push to GitHub**: Upload this code to a new GitHub repository.
2. **Create Web Service**:
   - Go to [Render Dashboard](https://dashboard.render.com/).
   - Click **"New +"** -> **"Background Worker"** (Recommended for bots) or "Web Service".
   - Connect your GitHub repo.
3. **Configure**:
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python bot.py`
4. **Environment Variables**:
   - Add all the variables from the "Local Testing" section above.
5. **Deploy**: Click "Create Background Worker".

The bot will now run 24/7!

## Configuration
- **RSS Feeds**: Edit the `RSS_FEEDS` list in `bot.py` to add your preferred sources.
- **Schedule**: The bot is set to sleep for 1800 seconds (30 mins) between posts.

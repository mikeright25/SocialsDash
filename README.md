# SocialsDash 🔖

> A lightweight, distraction-free personal dashboard running locally (`127.0.0.1`) to manage, organize, and read your personal Reddit saved items and subscribed feeds.

📖 **Full API & Reddit Compliance Guide:** See [API_DOCUMENTATION.md](API_DOCUMENTATION.md) for endpoint details and copy-paste developer review templates.

---

## 🌟 Overview

**SocialsDash** is a local-only productivity tool built for Reddit users who want to take control of their saved content and reading habits. Instead of losing saved posts in an endless, unorganized list, SocialsDash provides a clean personal library and distraction-free reader on your local machine.

### Key Capabilities
- **📁 Topic-Based Bookmark Organization:** Automatically syncs saved posts and comments from `GET /user/{username}/saved` and organizes them into customizable local topic folders (e.g., Tech & Engineering, AI, Productivity, Deep Reads, Design).
- **🏷️ Tags, Notes & Reading Status:** Add personal notes, custom tags, star favorites, and track reading status (`unread`, `reading`, `archived`).
- **📰 Subscribed Feed Reader:** Pulls your subscribed communities via `GET /subreddits/mine/subscriber` and provides an aggregated, chronological reading view tailored for focused reading.
- **🔒 100% Private & Local:** All bookmarks, folder mappings, and settings are saved strictly on your local disk in `data/*.json`. No cloud sync, external databases, tracking, or telemetry.
- **💾 Easy Export & Backup:** Export your entire library anytime as a single JSON file (`socialsdash-library-backup.json`).

---

## 📋 Reddit API Usage & Compliance

SocialsDash is designed strictly for personal account management using Reddit's standard OAuth Script authorization:

* **OAuth Script Authentication:** Authenticates via `POST /api/v1/access_token` using your personal script credentials to obtain short-lived Bearer tokens. Tokens are cached in-memory for their 1-hour lifespan to minimize authentication calls.
* **Saved Content:** Reads personal saved items via `GET /user/{username}/saved` to build a local bookmark database.
* **Subscribed Communities:** Reads subscribed subreddits via `GET /subreddits/mine/subscriber` to build a community switcher.
* **Distraction-Free Feed:** Reads feed posts via `GET /r/{subreddit}/{sort}` and `GET /{sort}` to display a clean, chronological reading list from your subscriptions.
* **Strictly Read-Only:** Performs no automated posting, voting, commenting, messaging, scraping, or moderation.
* **Rate-Limit Compliant:** All requests are manually triggered by the user and send compliant `User-Agent` headers operating well within Reddit's 100 req/min OAuth threshold.

👉 For complete API justifications and Reddit developer submission responses, consult [API_DOCUMENTATION.md](API_DOCUMENTATION.md).

---

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.9+
- A standard Reddit account

### 2. Clone & Install Dependencies
```bash
git clone https://github.com/mikeright25/SocialsDash.git
cd SocialsDash

# Create and activate virtual environment (optional but recommended)
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### 3. Get Your Reddit API Credentials (Instant & Free)
You **do not** have to wait for manual Reddit approval for personal use. You can generate credentials instantly:
1. Go to [https://www.reddit.com/prefs/apps](https://www.reddit.com/prefs/apps) (logged in).
2. Scroll to the bottom and click **"are you a developer? create an app..."** (or **"create another app..."**).
3. Fill out the form:
   - **name:** `SocialsDash`
   - **Select app type:** Choose **script** (personal use script). *Do not select web app or installed app.*
   - **description:** `Personal local bookmark organizer and reader`
   - **about url:** (can leave blank or `http://localhost:5000`)
   - **redirect uri:** `http://localhost:5000`
4. Click **create app**.
5. Your credentials appear immediately:
   - **Client ID:** The string displayed right below `personal use script` (under the app name).
   - **Client Secret:** The string next to `secret`.

### 4. Configure Credentials
Copy `.env.example` to `.env` and fill in your details:

```bash
cp .env.example .env
```

```env
REDDIT_CLIENT_ID=your_client_id_here
REDDIT_CLIENT_SECRET=your_client_secret_here
REDDIT_USERNAME=your_reddit_username
REDDIT_PASSWORD=your_reddit_password
REDDIT_USER_AGENT=desktop:SocialsDash:1.0 (by /u/your_reddit_username)
PORT=5000
```

*(Note: If you have Two-Factor Authentication / 2FA enabled on your Reddit account, append your 6-digit 2FA code to your password: `yourpassword:123456`).*

### 5. Launch the Application
```bash
python SocialsDash.py
```

The app will start on `http://127.0.0.1:5000` and automatically open your default browser.

---

## 📂 Project Structure

```text
SocialsDash/
├── data/                      # Local JSON storage (created automatically, gitignored)
│   ├── config.json            # Local configuration & credentials
│   ├── saved_content.json     # Synced saved posts & bookmark metadata
│   ├── subreddits.json        # Subscribed communities cache
│   └── folders.json           # User folder definitions
├── static/                    # Frontend styles, scripts & icons
├── templates/
│   └── index.html             # Single-page dashboard UI
├── .env.example               # Example environment variables template
├── requirements.txt           # Python dependencies (Flask, requests, python-dotenv)
├── SocialsDash.py             # Flask backend & Reddit OAuth integration
├── API_DOCUMENTATION.md       # Reddit API compliance & developer submission reference
└── README.md                  # Project overview and setup guide
```

---

## 🛡️ Privacy & Security

- **Localhost Only:** Runs exclusively on `127.0.0.1`.
- **No Remote Databases:** Zero analytics, telemetry, or external databases.
- **Excluded Secrets:** `.env` and `data/` are pre-configured in `.gitignore` to prevent leaking credentials.
- **No AI Training:** Reddit content is stored locally for personal reading and is never used to train models.

---

## 📄 License
MIT License. Created for personal, non-commercial use.
# SocialsDash - API Documentation & Reddit Developer Compliance

This document contains:
1. **Reddit Developer Review / App Justification**: Standardized responses for Reddit's API registration and developer intake forms.
2. **Reddit Endpoints Reference**: Details of external Reddit API endpoints consumed by SocialsDash.
3. **Local REST API Reference**: Specification of internal Flask endpoints powering the local dashboard.

🏠 **Main Project Guide:** See [README.md](README.md) for quick start, installation, and usage instructions.

---

## 1. Reddit Developer Review / Registration Justification

Use the following standardized responses if prompted during Reddit API developer registration:

### App Details
- **App Name**: `SocialsDash`
- **App Type**: `script` (Personal use script)
- **Redirect URI**: `http://localhost:5000`
- **User-Agent Format**: `desktop:SocialsDash:1.0 (by /u/mikeright25)`

### App Description & Purpose
> SocialsDash is a lightweight personal productivity application running locally on localhost (`127.0.0.1`) for personal account management. Specifically, it allows me to:
> 1. Authenticate via OAuth using standard script authorization for my own personal account.
> 2. Read my personal saved content via `GET /user/{username}/saved` to organize bookmarks into local topic folders, manage tags, and track reading status.
> 3. Read my subscribed subreddits via `GET /subreddits/mine/subscriber` to generate an aggregated local reading view and community navigator.
> 4. Read feed listings via `GET /r/{subreddit}/{sort}` and `GET /{sort}` to view posts from my subscribed communities in a clean, chronological reading interface.

### Endpoints Requested & Technical Rationale
| Endpoint | Method | Purpose / Justification |
| :--- | :---: | :--- |
| `https://www.reddit.com/api/v1/access_token` | `POST` | Authenticates using standard OAuth 2.0 password grant for script applications to obtain temporary Bearer access tokens. |
| `https://oauth.reddit.com/user/{username}/saved` | `GET` | Fetches my own saved submissions and comments (limit: 100) to index them into local topic folders (e.g., Tech, AI, Productivity). |
| `https://oauth.reddit.com/subreddits/mine/subscriber` | `GET` | Fetches the list of subreddits I personally subscribe to in order to display a navigation list of my communities. |
| `https://oauth.reddit.com/r/{subreddit}/{sort}` | `GET` | Fetches post listings for a chosen subscribed subreddit (limit: 35) for a focused reading view. |
| `https://oauth.reddit.com/{sort}` | `GET` | Fetches my personalized front-page feed (limit: 35) for an aggregated chronological view. |

### Data Storage, Privacy & Security
- **Local Storage Only**: All data is stored strictly on the local machine in `data/*.json`. No cloud databases, remote servers, or third-party storage are involved.
- **No Third-Party Sharing**: Data retrieved from Reddit is never sold, shared, re-broadcasted, or transmitted to external parties.
- **No AI Training**: Content is never used to train machine learning models or LLMs.
- **Read-Only Operation**: The application does not write back to Reddit. It does not submit posts, post comments, cast votes, send direct messages, or perform moderation tasks.

### Rate Limiting & Token Caching
- **Token Caching**: OAuth access tokens are cached in memory for their 3600-second (1 hour) validity window to prevent redundant token requests.
- **Manual Triggers**: API calls are made only when initiated by the user (clicking "Sync" or switching feeds). There are no background pollers or automated loops.
- **Rate Limit Adherence**: Request volume is typically <5 requests per session, operating well within Reddit's 100 requests per minute threshold.

---

## 2. Reddit OAuth Workflow (Internal Implementation)

SocialsDash uses HTTP Basic Authentication with client credentials to request a user token:

```http
POST https://www.reddit.com/api/v1/access_token
Authorization: Basic BASE64(client_id:client_secret)
Content-Type: application/x-www-form-urlencoded
User-Agent: desktop:SocialsDash:1.0 (by /u/mikeright25)

grant_type=password&username=<username>&password=<password>
```

Subsequent calls to Reddit use the bearer token:

```http
GET https://oauth.reddit.com/user/<username>/saved?limit=100
Authorization: Bearer <access_token>
User-Agent: desktop:SocialsDash:1.0 (by /u/mikeright25)
```

---

## 3. Local Flask Backend API Reference

The dashboard web interface communicates with the local Flask server (`http://127.0.0.1:5000`) through the following endpoints:

### Authentication & Status
* **`GET /api/auth/status`**
  * Checks if credentials exist and if an OAuth token can be obtained.
  * **Response**: `{"configured": bool, "authenticated": bool, "username": str, "error": str|null}`

* **`POST /api/auth/configure`**
  * Updates credentials (`client_id`, `client_secret`, `username`, `password`, `user_agent`) and tests connection.
  * **Payload**: `{"client_id": "...", "client_secret": "...", "username": "...", "password": "...", "user_agent": "..."}`

### Saved Content (Bookmarks)
* **`POST /api/saved/sync`**
  * Calls Reddit `GET /user/{username}/saved`, parses submissions/comments, auto-categorizes them into initial topic folders, and merges them into `data/saved_content.json`.
  * **Response**: `{"success": true, "message": "...", "total": int, "new": int}`

* **`GET /api/saved`**
  * Retrieves saved bookmarks with optional search and filtering.
  * **Query Params**:
    * `q`: text search query (title, author, subreddit, body, tags)
    * `folder`: filter by folder ID or `all`
    * `subreddit`: filter by subreddit name or `all`
    * `status`: filter by status (`unread`, `reading`, `archived`, or `all`)
    * `starred`: `true` to return only starred items

* **`PUT /api/saved/<item_id>`**
  * Updates local metadata for a saved item (folder ID, tags array, status, starred flag, user note).
  * **Payload**: `{"folderId": "...", "tags": [...], "status": "...", "isStarred": bool, "userNote": "..."}`

### Subscribed Communities & Feeds
* **`POST /api/subreddits/sync`**
  * Calls Reddit `GET /subreddits/mine/subscriber` and updates `data/subreddits.json`.
  * **Response**: `{"success": true, "count": int, "subreddits": [...]}`

* **`GET /api/subreddits`**
  * Returns the cached list of subscribed subreddits.

* **`GET /api/subreddits/feed`**
  * Fetches the live chronological post feed.
  * **Query Params**:
    * `subreddit`: subreddit name (e.g., `python`), or empty for frontpage
    * `sort`: `hot`, `new`, or `top` (default: `hot`)

### Topic Folders
* **`GET /api/folders`**
  * Lists all topic folders along with the current count of items in each folder.

* **`POST /api/folders`**
  * Creates a new user folder.
  * **Payload**: `{"name": "...", "color": "#hex", "icon": "..."}`

### Export & Backup
* **`GET /api/export`**
  * Generates and downloads a complete JSON backup of the library (`saved_content`, `folders`, and `subreddits`).

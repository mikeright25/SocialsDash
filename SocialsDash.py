#!/usr/bin/env python3
"""
SocialsDash - Personal Distraction-Free Reddit Organizer & Subscribed Feed Hub
Runs on localhost for personal account management.
- Reddit OAuth script authorization (client_id, client_secret, username, password)
- GET /user/{username}/saved -> Organizes bookmarks into local topic folders
- GET /subreddits/mine/subscriber -> Aggregated local reading view
- 100% private, local storage, distraction-free reading mode
"""

import os
import sys
import json
import time
import threading
import webbrowser
from datetime import datetime
from flask import Flask, request, jsonify, render_template, Response
import requests

# Load optional .env file if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static"
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")
SAVED_FILE = os.path.join(DATA_DIR, "saved_content.json")
SUBREDDITS_FILE = os.path.join(DATA_DIR, "subreddits.json")
FOLDERS_FILE = os.path.join(DATA_DIR, "folders.json")
NOTES_FILE = os.path.join(DATA_DIR, "notes.json")

os.makedirs(DATA_DIR, exist_ok=True)

# Default Topic Folders
DEFAULT_FOLDERS = [
    {"id": "folder_tech", "name": "Tech & Engineering", "color": "#0284c7", "icon": "code"},
    {"id": "folder_ai", "name": "AI & Machine Learning", "color": "#8b5cf6", "icon": "cpu"},
    {"id": "folder_productivity", "name": "Productivity & PKM", "color": "#10b981", "icon": "check-circle"},
    {"id": "folder_essays", "name": "Deep Reads & Discussions", "color": "#f59e0b", "icon": "book-open"},
    {"id": "folder_design", "name": "Design & UI/UX", "color": "#ec4899", "icon": "layout"},
    {"id": "folder_general", "name": "General & Backlog", "color": "#64748b", "icon": "folder"}
]

# In-memory token cache
token_cache = {
    "access_token": None,
    "expires_at": 0
}

def load_json(path, fallback):
    if not os.path.exists(path):
        save_json(path, fallback)
        return fallback
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading {path}: {e}")
        return fallback

def save_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving {path}: {e}")
        return False

def get_reddit_credentials():
    """Retrieve credentials from config.json or environment variables."""
    cfg = load_json(CONFIG_FILE, {})
    return {
        "client_id": cfg.get("client_id") or os.environ.get("REDDIT_CLIENT_ID", ""),
        "client_secret": cfg.get("client_secret") or os.environ.get("REDDIT_CLIENT_SECRET", ""),
        "username": cfg.get("username") or os.environ.get("REDDIT_USERNAME", ""),
        "password": cfg.get("password") or os.environ.get("REDDIT_PASSWORD", ""),
        "user_agent": cfg.get("user_agent") or os.environ.get("REDDIT_USER_AGENT", "SocialsDash:1.0 (personal dashboard)")
    }

def get_access_token():
    """Authenticate via OAuth using standard script authorization."""
    global token_cache
    now = time.time()
    if token_cache["access_token"] and token_cache["expires_at"] > now + 60:
        return token_cache["access_token"], None

    creds = get_reddit_credentials()
    if not (creds["client_id"] and creds["client_secret"] and creds["username"] and creds["password"]):
        return None, "Reddit OAuth credentials not configured. Please enter them in Settings or .env"

    try:
        auth = requests.auth.HTTPBasicAuth(creds["client_id"], creds["client_secret"])
        data = {
            "grant_type": "password",
            "username": creds["username"],
            "password": creds["password"]
        }
        headers = {"User-Agent": creds["user_agent"]}

        response = requests.post(
            "https://www.reddit.com/api/v1/access_token",
            auth=auth,
            data=data,
            headers=headers,
            timeout=10
        )

        if response.status_code != 200:
            return None, f"Authentication failed (HTTP {response.status_code}): {response.text}"

        res_data = response.json()
        if "error" in res_data:
            return None, f"Reddit OAuth error: {res_data.get('error')}"

        access_token = res_data.get("access_token")
        expires_in = res_data.get("expires_in", 3600)

        token_cache["access_token"] = access_token
        token_cache["expires_at"] = now + expires_in
        return access_token, None
    except Exception as e:
        return None, f"Network error during authentication: {str(e)}"

# ==================== WEB APP ROUTE ====================

@app.route("/")
def index():
    return render_template("index.html")

# ==================== AUTH & CONFIG API ====================

@app.route("/api/auth/status", methods=["GET"])
def auth_status():
    creds = get_reddit_credentials()
    has_creds = bool(creds["client_id"] and creds["client_secret"] and creds["username"] and creds["password"])
    token, err = get_access_token() if has_creds else (None, "Credentials missing")
    return jsonify({
        "configured": has_creds,
        "authenticated": bool(token),
        "username": creds.get("username", ""),
        "error": err if not token else None
    })

@app.route("/api/auth/configure", methods=["POST"])
def configure_auth():
    data = request.json or {}
    cfg = load_json(CONFIG_FILE, {})
    if "client_id" in data: cfg["client_id"] = data["client_id"].strip()
    if "client_secret" in data: cfg["client_secret"] = data["client_secret"].strip()
    if "username" in data: cfg["username"] = data["username"].strip()
    if "password" in data: cfg["password"] = data["password"].strip()
    if "user_agent" in data: cfg["user_agent"] = data["user_agent"].strip() or f"SocialsDash:1.0 (by /u/{cfg.get('username')})"

    save_json(CONFIG_FILE, cfg)
    token_cache["access_token"] = None  # Force re-auth
    token, err = get_access_token()

    if err:
        return jsonify({"success": False, "message": err}), 400
    return jsonify({"success": True, "message": "Successfully authenticated with Reddit!"})

# ==================== SAVED CONTENT API ====================

@app.route("/api/saved/sync", methods=["POST"])
def sync_saved_content():
    """Fetch saved content via GET /user/username/saved and merge into local library."""
    token, err = get_access_token()
    if not token:
        return jsonify({"success": False, "message": err}), 401

    creds = get_reddit_credentials()
    username = creds["username"]
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": creds["user_agent"]
    }

    try:
        # Fetch up to 100 recent saved items
        url = f"https://oauth.reddit.com/user/{username}/saved?limit=100"
        res = requests.get(url, headers=headers, timeout=12)

        if res.status_code != 200:
            return jsonify({"success": False, "message": f"Reddit API error ({res.status_code}): {res.text}"}), 400

        data = res.json()
        children = data.get("data", {}).get("children", [])

        current_saved = load_json(SAVED_FILE, [])
        saved_dict = {item["id"]: item for item in current_saved}

        new_count = 0
        for item in children:
            kind = item.get("kind") # t3 = submission, t1 = comment
            d = item.get("data", {})
            item_id = d.get("id")

            if not item_id:
                continue

            is_comment = kind == "t1"
            title = d.get("link_title", "") if is_comment else d.get("title", "")
            body = d.get("body", "") if is_comment else (d.get("selftext", "") or d.get("url", ""))

            # Suggest folder based on subreddit
            sub = d.get("subreddit", "").lower()
            default_folder = "folder_general"
            if sub in ["python", "programming", "webdev", "coding", "softwareengineering"]:
                default_folder = "folder_tech"
            elif sub in ["machinelearning", "localllama", "artificial", "openai", "claudeai"]:
                default_folder = "folder_ai"
            elif sub in ["productivity", "obsidianmd", "notion", "pkm", "gtd"]:
                default_folder = "folder_productivity"
            elif sub in ["ui_design", "web_design", "css", "frontend"]:
                default_folder = "folder_design"
            elif sub in ["depthhub", "truereddit", "philosophy", "books"]:
                default_folder = "folder_essays"

            if item_id in saved_dict:
                # Keep user-customized local metadata
                saved_dict[item_id]["score"] = d.get("score", saved_dict[item_id].get("score", 0))
                saved_dict[item_id]["num_comments"] = d.get("num_comments", saved_dict[item_id].get("num_comments", 0))
            else:
                new_count += 1
                saved_dict[item_id] = {
                    "id": item_id,
                    "fullname": d.get("name", f"{kind}_{item_id}"),
                    "kind": kind,
                    "title": title or "Untitled Saved Item",
                    "author": d.get("author", "[deleted]"),
                    "subreddit": d.get("subreddit", ""),
                    "permalink": f"https://reddit.com{d.get('permalink', '')}",
                    "url": d.get("url", ""),
                    "body": body,
                    "score": d.get("score", 0),
                    "num_comments": d.get("num_comments", 0),
                    "created_utc": d.get("created_utc", time.time()),
                    "thumbnail": d.get("thumbnail", "") if not is_comment else "",
                    "is_self": d.get("is_self", False),
                    "folderId": default_folder,
                    "tags": [d.get("subreddit", "")] if d.get("subreddit") else [],
                    "status": "unread", # unread, reading, archived
                    "isStarred": False,
                    "syncedAt": datetime.utcnow().isoformat() + "Z"
                }

        merged_saved = list(saved_dict.values())
        merged_saved.sort(key=lambda x: x.get("created_utc", 0), reverse=True)
        save_json(SAVED_FILE, merged_saved)

        return jsonify({
            "success": True,
            "message": f"Sync complete! Retrieved {len(children)} items ({new_count} new).",
            "total": len(merged_saved),
            "new": new_count
        })

    except Exception as e:
        return jsonify({"success": False, "message": f"Sync failed: {str(e)}"}), 500

@app.route("/api/saved", methods=["GET"])
def get_saved():
    """Retrieve saved bookmarks with filters."""
    items = load_json(SAVED_FILE, [])
    q = request.args.get("q", "").strip().lower()
    folder_id = request.args.get("folder", "all")
    subreddit = request.args.get("subreddit", "all")
    status = request.args.get("status", "all")
    starred = request.args.get("starred", "")

    if q:
        items = [
            it for it in items
            if q in it.get("title", "").lower()
            or q in it.get("author", "").lower()
            or q in it.get("subreddit", "").lower()
            or q in it.get("body", "").lower()
            or any(q in t.lower() for t in it.get("tags", []))
        ]

    if folder_id != "all":
        items = [it for it in items if it.get("folderId") == folder_id]

    if subreddit != "all":
        items = [it for it in items if it.get("subreddit", "").lower() == subreddit.lower()]

    if status != "all":
        items = [it for it in items if it.get("status") == status]

    if starred == "true":
        items = [it for it in items if it.get("isStarred") is True]

    return jsonify({"success": True, "count": len(items), "items": items})

@app.route("/api/saved/<item_id>", methods=["PUT"])
def update_saved_item(item_id):
    """Update folder, tags, status, starred, or notes for a saved item."""
    items = load_json(SAVED_FILE, [])
    data = request.json or {}

    found = False
    updated_item = None
    for item in items:
        if item.get("id") == item_id:
            if "folderId" in data: item["folderId"] = data["folderId"]
            if "tags" in data: item["tags"] = data["tags"]
            if "status" in data: item["status"] = data["status"]
            if "isStarred" in data: item["isStarred"] = data["isStarred"]
            if "userNote" in data: item["userNote"] = data["userNote"]
            updated_item = item
            found = True
            break

    if not found:
        return jsonify({"success": False, "message": "Item not found"}), 404

    save_json(SAVED_FILE, items)
    return jsonify({"success": True, "item": updated_item})

# ==================== SUBSCRIBED SUBREDDITS API ====================

@app.route("/api/subreddits/sync", methods=["POST"])
def sync_subreddits():
    """Fetch subscribed subreddits via GET /subreddits/mine/subscriber."""
    token, err = get_access_token()
    if not token:
        return jsonify({"success": False, "message": err}), 401

    creds = get_reddit_credentials()
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": creds["user_agent"]
    }

    try:
        url = "https://oauth.reddit.com/subreddits/mine/subscriber?limit=100"
        res = requests.get(url, headers=headers, timeout=12)

        if res.status_code != 200:
            return jsonify({"success": False, "message": f"Reddit API error ({res.status_code}): {res.text}"}), 400

        data = res.json()
        children = data.get("data", {}).get("children", [])

        subs = []
        for c in children:
            d = c.get("data", {})
            subs.append({
                "id": d.get("id"),
                "display_name": d.get("display_name"),
                "title": d.get("title", ""),
                "description": d.get("public_description", ""),
                "subscribers": d.get("subscribers", 0),
                "icon": d.get("community_icon") or d.get("icon_img") or "",
                "url": d.get("url", f"/r/{d.get('display_name')}/"),
                "over18": d.get("over18", False)
            })

        subs.sort(key=lambda x: x["display_name"].lower())
        save_json(SUBREDDITS_FILE, subs)

        return jsonify({
            "success": True,
            "message": f"Subscribed subreddits synced successfully ({len(subs)} communities).",
            "count": len(subs),
            "subreddits": subs
        })

    except Exception as e:
        return jsonify({"success": False, "message": f"Subreddit sync failed: {str(e)}"}), 500

@app.route("/api/subreddits", methods=["GET"])
def get_subreddits():
    subs = load_json(SUBREDDITS_FILE, [])
    return jsonify({"success": True, "count": len(subs), "subreddits": subs})

@app.route("/api/subreddits/feed", methods=["GET"])
def get_aggregated_feed():
    """Aggregated local distraction-free reading view from subscribed subreddits."""
    token, err = get_access_token()
    if not token:
        return jsonify({"success": False, "message": err}), 401

    creds = get_reddit_credentials()
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": creds["user_agent"]
    }

    subreddit = request.args.get("subreddit", "").strip()
    sort_mode = request.args.get("sort", "hot") # hot, new, top

    try:
        # If specific subreddit requested, fetch r/{sub}/{sort}. Otherwise fetch personalized frontpage /hot
        endpoint = f"https://oauth.reddit.com/r/{subreddit}/{sort_mode}?limit=35" if subreddit else f"https://oauth.reddit.com/{sort_mode}?limit=35"
        res = requests.get(endpoint, headers=headers, timeout=12)

        if res.status_code != 200:
            return jsonify({"success": False, "message": f"Reddit API error ({res.status_code}): {res.text}"}), 400

        data = res.json()
        children = data.get("data", {}).get("children", [])

        feed_items = []
        for c in children:
            d = c.get("data", {})
            # Filter out promoted / stickied ads
            if d.get("promoted", False):
                continue

            feed_items.append({
                "id": d.get("id"),
                "name": d.get("name"),
                "title": d.get("title", "Untitled Post"),
                "author": d.get("author", "[deleted]"),
                "subreddit": d.get("subreddit", ""),
                "permalink": f"https://reddit.com{d.get('permalink', '')}",
                "url": d.get("url", ""),
                "selftext": d.get("selftext", ""),
                "score": d.get("score", 0),
                "num_comments": d.get("num_comments", 0),
                "created_utc": d.get("created_utc", 0),
                "thumbnail": d.get("thumbnail", "") if not d.get("is_self") else "",
                "is_self": d.get("is_self", False),
                "post_hint": d.get("post_hint", "")
            })

        return jsonify({"success": True, "count": len(feed_items), "items": feed_items})

    except Exception as e:
        return jsonify({"success": False, "message": f"Feed error: {str(e)}"}), 500

# ==================== TOPIC FOLDERS API ====================

@app.route("/api/folders", methods=["GET"])
def get_folders():
    folders = load_json(FOLDERS_FILE, DEFAULT_FOLDERS)
    saved_items = load_json(SAVED_FILE, [])

    # Calculate item count per folder
    counts = {}
    for it in saved_items:
        fid = it.get("folderId", "folder_general")
        counts[fid] = counts.get(fid, 0) + 1

    for f in folders:
        f["itemCount"] = counts.get(f["id"], 0)

    return jsonify({"success": True, "folders": folders})

@app.route("/api/folders", methods=["POST"])
def create_folder():
    folders = load_json(FOLDERS_FILE, DEFAULT_FOLDERS)
    data = request.json or {}
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"success": False, "message": "Folder name is required"}), 400

    new_folder = {
        "id": f"folder_{int(time.time() * 1000)}",
        "name": name,
        "color": data.get("color", "#0284c7"),
        "icon": data.get("icon", "folder"),
        "itemCount": 0
    }
    folders.append(new_folder)
    save_json(FOLDERS_FILE, folders)
    return jsonify({"success": True, "folder": new_folder}), 201

# ==================== EXPORT / IMPORT API ====================

@app.route("/api/export", methods=["GET"])
def export_library():
    export_data = {
        "version": "1.0.0",
        "exportedAt": datetime.utcnow().isoformat() + "Z",
        "saved_content": load_json(SAVED_FILE, []),
        "folders": load_json(FOLDERS_FILE, DEFAULT_FOLDERS),
        "subreddits": load_json(SUBREDDITS_FILE, [])
    }
    return Response(
        json.dumps(export_data, indent=2, ensure_ascii=False),
        mimetype="application/json",
        headers={"Content-Disposition": "attachment; filename=socialsdash-library-backup.json"}
    )

def open_browser(port):
    time.sleep(1.2)
    url = f"http://127.0.0.1:{port}"
    print(f">> Opening browser to {url} ...")
    webbrowser.open(url)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("=" * 65)
    print(" SocialsDash - Personal Distraction-Free Reddit Organizer")
    print(f" Web UI running at: http://127.0.0.1:{port}")
    print("=" * 65)

    if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        threading.Thread(target=open_browser, args=(port,), daemon=True).start()

    app.run(host="127.0.0.1", port=port, debug=False)

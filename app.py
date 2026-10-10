import os
import re
import requests

from flask import Flask, request, jsonify

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
API_KEY = os.environ.get("API_KEY", "")

TELEGRAM_API = (
    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
)


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "app": "TG INFO PRO API",
        "status": "success",
        "message": "API is running",
        "endpoints": [
            "/health",
            "/api/user-info",
            "/api/group-member"
        ]
    })


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok"
    })


def authorized():
    supplied_key = request.headers.get("X-API-Key", "")

    return bool(API_KEY) and supplied_key == API_KEY


def telegram_request(method, params):
    response = requests.get(
        f"{TELEGRAM_API}/{method}",
        params=params,
        timeout=15
    )

    response.raise_for_status()
    data = response.json()

    if not data.get("ok"):
        raise ValueError(
            data.get("description", "Telegram API error")
        )

    return data["result"]


@app.route("/api/user-info", methods=["GET"])
def user_info():
    if not authorized():
        return jsonify({
            "ok": False,
            "error": "Unauthorized"
        }), 401

    if not TELEGRAM_BOT_TOKEN:
        return jsonify({
            "ok": False,
            "error": "Telegram bot token is not configured"
        }), 503

    identifier = request.args.get("identifier", "").strip()

    if not identifier:
        return jsonify({
            "ok": False,
            "error": "identifier is required"
        }), 400

    # Accept numeric Telegram IDs or usernames.
    if identifier.startswith("@"):
        username = identifier[1:]

        if not re.fullmatch(r"[A-Za-z0-9_]{5,32}", username):
            return jsonify({
                "ok": False,
                "error": "Invalid username format"
            }), 400

        chat_id = "@" + username

    elif re.fullmatch(r"[0-9]{1,20}", identifier):
        chat_id = identifier

    else:
        return jsonify({
            "ok": False,
            "error": "Send a numeric ID or @username"
        }), 400

    try:
        chat = telegram_request(
            "getChat",
            {"chat_id": chat_id}
        )

        result = {
            "ok": True,
            "id": chat.get("id"),
            "type": chat.get("type"),
            "first_name": chat.get("first_name"),
            "last_name": chat.get("last_name"),
            "username": chat.get("username"),
            "title": chat.get("title"),
            "is_bot": chat.get("is_bot"),
            "note": (
                "Only information returned by Telegram "
                "for this accessible chat is included."
            )
        }

        return jsonify(result)

    except requests.RequestException:
        return jsonify({
            "ok": False,
            "error": "Could not connect to Telegram"
        }), 502

    except ValueError as exc:
        return jsonify({
            "ok": False,
            "error": str(exc)
        }), 400


@app.route("/api/group-member", methods=["GET"])
def group_member():
    if not authorized():
        return jsonify({
            "ok": False,
            "error": "Unauthorized"
        }), 401

    if not TELEGRAM_BOT_TOKEN:
        return jsonify({
            "ok": False,
            "error": "Telegram bot token is not configured"
        }), 503

    group_id = request.args.get("group_id", "").strip()
    user_id = request.args.get("user_id", "").strip()

    if not group_id or not re.fullmatch(r"-?[0-9]{1,20}", group_id):
        return jsonify({
            "ok": False,
            "error": "A numeric group_id is required"
        }), 400

    if not user_id or not re.fullmatch(r"[0-9]{1,20}", user_id):
        return jsonify({
            "ok": False,
            "error": "A numeric user_id is required"
        }), 400

    try:
        member = telegram_request(
            "getChatMember",
            {
                "chat_id": group_id,
                "user_id": user_id
            }
        )

        user = member.get("user", {})

        return jsonify({
            "ok": True,
            "user_id": user.get("id"),
            "first_name": user.get("first_name"),
            "last_name": user.get("last_name"),
            "username": user.get("username"),
            "is_bot": user.get("is_bot"),
            "status": member.get("status"),
            "is_member": member.get("status") in [
                "creator",
                "administrator",
                "member"
            ]
        })

    except requests.RequestException:
        return jsonify({
            "ok": False,
            "error": "Could not connect to Telegram"
        }), 502

    except ValueError as exc:
        return jsonify({
            "ok": False,
            "error": str(exc)
        }), 400


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 10000))
      )

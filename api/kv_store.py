#!/usr/bin/env python3
"""
Author: Tim Smith
Note: All Code owned by Tim

Vercel KV (Upstash Redis) client for storing email subscriptions.
Set up: Vercel dashboard → Storage → Create KV Database
Env vars auto-set by Vercel: KV_REST_API_URL, KV_REST_API_TOKEN
"""

import os
import json
import requests

KV_URL = os.environ.get('KV_REST_API_URL', '')
KV_TOKEN = os.environ.get('KV_REST_API_TOKEN', '')


def is_available() -> bool:
    return bool(KV_URL and KV_TOKEN)


def _headers() -> dict:
    return {'Authorization': f'Bearer {KV_TOKEN}'}


def save_subscriber(email: str, profile: dict) -> bool:
    """Store a subscriber's email and profile in Vercel KV."""
    if not is_available():
        return False
    try:
        key = f'subscriber:{email.lower().strip()}'
        value = json.dumps(profile)
        # Upstash REST: POST /set/{key} with body as the value
        r = requests.post(
            f'{KV_URL}/set/{key}',
            headers={**_headers(), 'Content-Type': 'application/json'},
            data=json.dumps(value),
            timeout=5
        )
        return r.status_code == 200
    except Exception as e:
        print(f"KV save error: {e}")
        return False


def unsubscribe(email: str) -> bool:
    """Remove a subscriber from Vercel KV."""
    if not is_available():
        return False
    try:
        key = f'subscriber:{email.lower().strip()}'
        r = requests.get(f'{KV_URL}/del/{key}', headers=_headers(), timeout=5)
        return r.status_code == 200
    except Exception as e:
        print(f"KV delete error: {e}")
        return False


def get_all_subscribers() -> list:
    """Return list of {email, profile} dicts for all subscribers."""
    if not is_available():
        return []
    try:
        # Get all keys matching subscriber:*
        r = requests.get(f'{KV_URL}/keys/subscriber:*', headers=_headers(), timeout=5)
        if r.status_code != 200:
            return []

        keys = r.json().get('result', [])
        subscribers = []

        for key in keys:
            try:
                val_r = requests.get(f'{KV_URL}/get/{key}', headers=_headers(), timeout=5)
                if val_r.status_code != 200:
                    continue
                raw = val_r.json().get('result')
                if not raw:
                    continue
                profile = json.loads(raw) if isinstance(raw, str) else raw
                email = key.replace('subscriber:', '')
                subscribers.append({'email': email, 'profile': profile})
            except Exception:
                continue

        return subscribers
    except Exception as e:
        print(f"KV get all error: {e}")
        return []

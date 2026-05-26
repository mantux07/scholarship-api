#!/usr/bin/env python3
"""
Author: Tim Smith
Note: All Code owned by Tim

CareerOneStop Scholarship API Client (US Dept. of Labor)
Free API — register at https://developer.careeronestop.org
Env vars required: CAREERONESTOP_USER_ID, CAREERONESTOP_API_KEY
"""

import os
import requests
from datetime import datetime

USER_ID = os.environ.get('CAREERONESTOP_USER_ID', '')
API_KEY = os.environ.get('CAREERONESTOP_API_KEY', '')
BASE_URL = 'https://api.careeronestop.org/v1/scholarship'


def is_available() -> bool:
    return bool(USER_ID and API_KEY)


def search(student_profile: dict) -> list:
    """Search CareerOneStop for scholarships matching the student profile."""
    if not is_available():
        return []

    major = student_profile.get('major', '')
    state = student_profile.get('state', '')
    heritage = student_profile.get('heritage', '')

    # Build a small set of targeted queries
    queries = [q for q in [major, heritage] if q and q not in ('Not specified', '')]
    if not queries:
        queries = ['scholarship']

    results = []
    seen_names = set()

    for keyword in queries[:2]:
        try:
            items = _query(keyword, state)
            for item in items:
                if item['name'] not in seen_names:
                    seen_names.add(item['name'])
                    results.append(item)
        except Exception as e:
            print(f"CareerOneStop query error ({keyword}): {e}")

    return results[:25]


def _query(keyword: str, state: str) -> list:
    location = state if state and state not in ('Not specified', '') else 'United+States'
    keyword_enc = keyword.replace(' ', '+')
    url = f"{BASE_URL}/{USER_ID}/{keyword_enc}/{location}/0/all/deadline/asc/25"

    response = requests.get(
        url,
        headers={'Authorization': f'Bearer {API_KEY}'},
        timeout=8
    )

    if response.status_code != 200:
        return []

    data = response.json()
    today = datetime.now()
    scholarships = []

    for item in data.get('ScholarshipList', []):
        name = (item.get('ScholarshipName') or '').strip()
        if not name:
            continue

        try:
            amount_min = int(item.get('AwardMin') or 0)
            amount_max = int(item.get('AwardMax') or 0)
        except (ValueError, TypeError):
            amount_min = amount_max = 0

        if amount_min == 0 and amount_max == 0:
            amount_display = 'Varies'
        elif amount_min == amount_max:
            amount_display = f'${amount_max:,}'
        else:
            amount_display = f'${amount_min:,}–${amount_max:,}'

        deadline_str = (item.get('ScholarshipDeadline') or 'TBD').strip()
        days_until = 999
        for fmt in ('%m/%d/%Y', '%Y-%m-%d', '%B %d, %Y'):
            try:
                dl = datetime.strptime(deadline_str, fmt)
                days_until = (dl - today).days
                break
            except ValueError:
                continue
        if days_until < 0:
            continue  # Skip expired

        avg = (amount_min + amount_max) / 2 if (amount_min or amount_max) else 1000
        urgency = 30 if days_until < 30 else 20 if days_until < 90 else 10
        priority = round(min(40, avg / 500) + urgency + 15 + 7, 2)

        scholarships.append({
            'name': name,
            'amount_display': amount_display,
            'amount_min': amount_min,
            'amount_max': amount_max,
            'deadline': deadline_str,
            'days_until_deadline': days_until,
            'min_gpa': 0.0,
            'recommended_gpa': 0.0,
            'essay_required': False,
            'essay_word_count': 0,
            'rec_letters_required': 0,
            'interview_required': False,
            'competitiveness': 'Medium',
            'category': 'National',
            'renewable': False,
            'estimated_hours': 3.0,
            'application_url': (item.get('ContactWebsite') or '#'),
            'notes': (item.get('ScholarshipDescription') or '')[:300],
            'priority_score': priority,
            'source': 'CareerOneStop'
        })

    return scholarships

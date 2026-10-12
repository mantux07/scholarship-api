#!/usr/bin/env python3
"""
Author: Tim Smith
Note: All Code owned by Tim

Claude AI Scholarship Suggestions
Uses Claude to surface niche/lesser-known scholarships based on student profile.
Env var required: ANTHROPIC_API_KEY
"""

import os
import json
import logging
from datetime import datetime

log = logging.getLogger(__name__)

ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')


def is_available() -> bool:
    return bool(ANTHROPIC_API_KEY)


def get_suggestions(student_profile: dict) -> list:
    """Ask Claude for scholarship suggestions that match the student's profile."""
    if not is_available():
        return []

    try:
        import anthropic
        # Stay under index.py's AI_SUGGESTIONS_TIMEOUT so the worker thread doesn't outlive the request.
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY, timeout=18.0, max_retries=1)

        message = client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=2048,
            system=[{
                'type': 'text',
                'text': (
                    'You are a scholarship research expert with deep knowledge of US scholarships, '
                    'fellowships, grants, and research programs. You specialize in finding niche, '
                    'lesser-known opportunities that match specific student profiles. '
                    'You only suggest real, verifiable scholarships with accurate details.'
                ),
                'cache_control': {'type': 'ephemeral'}
            }],
            messages=[{
                'role': 'user',
                'content': f"""Find 12 real scholarships for this student. Prioritize niche, heritage-specific, state-specific, and field-specific opportunities they are unlikely to find through a basic Google search.

{_need_instruction(student_profile)}

{_format_profile(student_profile)}

Return ONLY a valid JSON array — no other text, no markdown. Each object must have exactly these fields:
{{
  "name": "Full official scholarship name",
  "amount_display": "e.g. $5,000 or $2,000–$10,000 or Varies",
  "amount_min": 0,
  "amount_max": 0,
  "deadline": "Month DD, YYYY for the 2026–2027 cycle or Varies or Rolling",
  "eligibility": "one sentence describing who qualifies",
  "application_url": "https://...",
  "notes": "1-2 sentences on why this matches the student",
  "category": "one of: National, Diversity, STEM, State, Corporate, Research, Merit, Disability, Military"
}}"""
            }]
        )

        raw = message.content[0].text.strip()
        log.debug("Claude raw response (first 500 chars): %s", raw[:500])

        start = raw.find('[')
        end = raw.rfind(']') + 1
        if start < 0 or end <= start:
            log.warning("Claude response contained no JSON array (first 200 chars: %r)", raw[:200])
            return []

        suggestions = json.loads(raw[start:end])
        if not isinstance(suggestions, list):
            log.warning("Claude JSON was not a list; ignoring")
            return []

        results = []
        for s in suggestions:
            if not isinstance(s, dict) or not s.get('name'):
                continue
            try:
                results.append(_normalize(s))
            except Exception:
                log.warning("Could not normalize Claude suggestion %r", s.get('name'), exc_info=True)
        log.info("Claude suggestions: %d parsed, %d usable", len(suggestions), len(results))
        return results

    except json.JSONDecodeError:
        log.warning("Claude returned malformed JSON; no AI suggestions this search")
        return []
    except Exception:
        log.exception("Claude suggestions request failed")
        return []


def _parse_amount(val) -> int:
    """Parse an amount value that may be int, float, or a formatted string like '5,000'."""
    if not val:
        return 0
    try:
        # Remove currency symbols, commas, spaces; handle floats
        cleaned = str(val).replace('$', '').replace(',', '').replace(' ', '').strip()
        return max(0, int(float(cleaned)))
    except (ValueError, TypeError):
        return 0


def _normalize(s: dict) -> dict:
    """Convert a Claude suggestion dict into the standard scholarship dict format."""
    today = datetime.now()
    deadline_str = s.get('deadline', 'Varies') or 'Varies'
    days_until = 999

    for fmt in ('%B %d, %Y', '%b %d, %Y', '%m/%d/%Y'):
        try:
            dl = datetime.strptime(deadline_str, fmt)
            while dl < today:
                dl = dl.replace(year=dl.year + 1)
            days_until = (dl - today).days
            deadline_str = dl.strftime('%B %d, %Y')
            break
        except ValueError:
            continue

    amount_min = _parse_amount(s.get('amount_min'))
    amount_max = _parse_amount(s.get('amount_max'))
    avg = (amount_min + amount_max) / 2 if (amount_min or amount_max) else 1000
    urgency = 25 if days_until < 30 else 15 if days_until < 90 else 10
    priority = round(min(35, avg / 600) + urgency + 12 + 7, 2)

    notes = s.get('notes', '')
    eligibility = s.get('eligibility', '')
    combined_notes = f"{notes} | Eligibility: {eligibility}".strip(' |')

    return {
        'name': s.get('name', ''),
        'amount_display': s.get('amount_display', 'Varies'),
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
        'category': s.get('category', 'National'),
        'renewable': False,
        'estimated_hours': 3.0,
        'application_url': s.get('application_url', '#'),
        'notes': combined_notes,
        'priority_score': priority,
        'source': 'AI Suggested'
    }


def _need_instruction(p: dict) -> str:
    if p.get('financial_need'):
        return ('The student has financial need, so need-based awards are welcome alongside merit awards. '
                'Say so in "eligibility" when an award requires financial need.')
    return 'Suggest merit-based awards only. Exclude anything that requires demonstrated financial need.'


def _format_profile(p: dict) -> str:
    fields = [
        ('University', 'university'),
        ('Major', 'major'),
        ('Year', 'year'),
        ('GPA', 'gpa'),
        ('Heritage/Ethnicity', 'heritage'),
        ('Gender', 'gender'),
        ('Home State', 'state'),
        ('Residency', 'residency'),
        ('First-generation student', 'first_gen'),
        ('Military affiliated', 'military'),
        ('Research interest', 'research'),
        ('Disability', 'disability'),
        ('Skills', 'skills'),
        ('Clubs/Organizations', 'clubs'),
        ('Athletics', 'athletics'),
        ('Discipline/Specialization', 'discipline'),
    ]
    lines = ['Student Profile:']
    for label, key in fields:
        val = p.get(key)
        if val and str(val).lower() not in ('not specified', 'false', '', 'general'):
            lines.append(f'  {label}: {val}')
    return '\n'.join(lines)

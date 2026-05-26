#!/usr/bin/env python3
"""
Author: Tim Smith
Note: All Code owned by Tim

Email client using SMTP (Hostinger or any SMTP provider).
Uses Python standard library only — no extra packages required.

Env vars required:
  SMTP_HOST      e.g. smtp.hostinger.com
  SMTP_PORT      587 (TLS) or 465 (SSL) — defaults to 587
  SMTP_USERNAME  your full email address e.g. alerts@tsprofits.com
  SMTP_PASSWORD  your email account password
  FROM_EMAIL     display address (defaults to SMTP_USERNAME)
  APP_URL        your site URL for links in emails
"""

import os
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

SMTP_HOST = os.environ.get('SMTP_HOST', 'smtp.hostinger.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', '587'))
SMTP_USERNAME = os.environ.get('SMTP_USERNAME', '')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')
FROM_EMAIL = os.environ.get('FROM_EMAIL', SMTP_USERNAME)
APP_URL = os.environ.get('APP_URL', 'https://scholarship-vercel-ebon.vercel.app')


def is_available() -> bool:
    return bool(SMTP_HOST and SMTP_USERNAME and SMTP_PASSWORD)


def send_confirmation(to_email: str, profile: dict) -> bool:
    """Send a subscription confirmation email."""
    if not is_available():
        return False

    university = profile.get('university', 'your university')
    major = profile.get('major', 'your major')
    gpa = profile.get('gpa', '')

    html = f"""
    <div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;max-width:600px;margin:0 auto">
      <div style="background:linear-gradient(135deg,#667eea,#764ba2);padding:30px;border-radius:12px 12px 0 0;text-align:center">
        <h1 style="color:white;margin:0;font-size:1.8em">🎓 Scholarship Alerts</h1>
        <p style="color:rgba(255,255,255,0.9);margin:8px 0 0">You're subscribed!</p>
      </div>
      <div style="background:white;padding:30px;border-radius:0 0 12px 12px;border:1px solid #e2e8f0;border-top:none">
        <p style="color:#2d3748;font-size:1.1em">We'll send you weekly updates with new scholarships matching your profile:</p>
        <div style="background:#f7fafc;border-left:4px solid #667eea;padding:16px;border-radius:0 8px 8px 0;margin:20px 0">
          <p style="margin:4px 0"><strong>University:</strong> {university}</p>
          <p style="margin:4px 0"><strong>Major:</strong> {major}</p>
          {"<p style='margin:4px 0'><strong>GPA:</strong> " + str(gpa) + "</p>" if gpa else ""}
        </div>
        <p style="color:#718096;font-size:0.9em">Emails arrive every Monday morning. You can unsubscribe at any time.</p>
        <div style="text-align:center;margin-top:24px">
          <a href="{APP_URL}" style="background:linear-gradient(135deg,#667eea,#764ba2);color:white;padding:14px 28px;border-radius:8px;text-decoration:none;font-weight:600;display:inline-block">
            Search Scholarships Now →
          </a>
        </div>
      </div>
    </div>
    """

    return _send(to_email, "✅ Scholarship Alerts — You're subscribed!", html)


def send_weekly_alert(to_email: str, scholarships: list, profile: dict) -> bool:
    """Send weekly scholarship digest to a subscriber."""
    if not is_available() or not scholarships:
        return False

    urgent = [s for s in scholarships
              if isinstance(s.get('days_until_deadline'), int)
              and 0 < s['days_until_deadline'] <= 30]
    featured = scholarships[:6]

    cards_html = ''
    for s in featured:
        days = s.get('days_until_deadline')
        deadline_color = '#f56565' if isinstance(days, int) and days <= 30 else '#2d3748'
        source_badge = (
            f'<span style="background:#e9d8fd;color:#553c9a;padding:2px 8px;border-radius:12px;font-size:0.8em;margin-left:8px">'
            f'{s.get("source", "")}</span>'
            if s.get('source') else ''
        )
        cards_html += f"""
        <div style="border:1px solid #e2e8f0;border-radius:8px;padding:16px;margin-bottom:12px">
          <h3 style="margin:0 0 8px;color:#2d3748;font-size:1em">
            {s['name']}{source_badge}
          </h3>
          <p style="margin:4px 0;color:#4a5568"><strong>Award:</strong> {s['amount_display']}</p>
          <p style="margin:4px 0;color:{deadline_color}"><strong>Deadline:</strong> {s['deadline']}
            {f"({days} days)" if isinstance(days, int) and days < 999 else ""}
          </p>
          <a href="{s['application_url']}" style="color:#667eea;font-weight:600">Apply Now →</a>
        </div>"""

    urgent_banner = (
        f'<div style="background:#fff5f5;border:1px solid #fc8181;border-radius:8px;padding:12px;margin-bottom:20px;color:#c53030">'
        f'⚠️ <strong>{len(urgent)} scholarship{"s" if len(urgent) > 1 else ""} expire within 30 days!</strong>'
        f'</div>'
    ) if urgent else ''

    university = profile.get('university', '')
    major = profile.get('major', '')

    html = f"""
    <div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;max-width:600px;margin:0 auto">
      <div style="background:linear-gradient(135deg,#667eea,#764ba2);padding:24px;border-radius:12px 12px 0 0;text-align:center">
        <h1 style="color:white;margin:0;font-size:1.5em">🎓 Your Weekly Scholarship Update</h1>
        <p style="color:rgba(255,255,255,0.9);margin:8px 0 0">{university} · {major}</p>
      </div>
      <div style="background:white;padding:24px;border-radius:0 0 12px 12px;border:1px solid #e2e8f0;border-top:none">
        <p style="color:#2d3748">We found <strong>{len(scholarships)} scholarships</strong> matching your profile this week.</p>
        {urgent_banner}
        <h2 style="color:#4a5568;font-size:1em;text-transform:uppercase;letter-spacing:0.05em">Top Matches</h2>
        {cards_html}
        <div style="text-align:center;margin-top:24px">
          <a href="{APP_URL}" style="background:linear-gradient(135deg,#667eea,#764ba2);color:white;padding:14px 28px;border-radius:8px;text-decoration:none;font-weight:600;display:inline-block">
            View All {len(scholarships)} Scholarships →
          </a>
        </div>
        <p style="color:#a0aec0;font-size:0.8em;text-align:center;margin-top:20px">
          <a href="{APP_URL}/api/unsubscribe?email={to_email}" style="color:#a0aec0">Unsubscribe</a>
        </p>
      </div>
    </div>
    """

    subject = f'🎓 {len(scholarships)} scholarships match your profile'
    if urgent:
        subject += f' — {len(urgent)} expiring soon!'
    return _send(to_email, subject, html)


def _send(to_email: str, subject: str, html: str) -> bool:
    """Send an HTML email via SMTP."""
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = FROM_EMAIL
        msg['To'] = to_email
        msg.attach(MIMEText(html, 'html'))

        if SMTP_PORT == 465:
            # SSL connection
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context) as server:
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
                server.sendmail(FROM_EMAIL, to_email, msg.as_string())
        else:
            # STARTTLS (port 587)
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                server.ehlo()
                server.starttls(context=ssl.create_default_context())
                server.ehlo()
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
                server.sendmail(FROM_EMAIL, to_email, msg.as_string())

        return True
    except Exception as e:
        print(f"Email send error: {e}")
        return False

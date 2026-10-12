#!/usr/bin/env python3
"""
Author: Tim Smith
Note: All Code owned by Tim

Flask API Backend for Scholarship Research Web App
Adapted for Vercel serverless deployment
"""

import sys
import os
import io
import logging
import time
import uuid

# Add the api/ directory to sys.path so sibling modules are importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, request, jsonify, send_file, send_from_directory, g
from flask_cors import CORS
from werkzeug.exceptions import HTTPException
import tempfile
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

# Vercel captures stdout/stderr as function logs. LOG_LEVEL=DEBUG shows
# skipped duplicates and other per-listing detail.
logging.basicConfig(
    level=os.environ.get('LOG_LEVEL', 'INFO').upper(),
    format='%(levelname)s %(name)s: %(message)s',
    stream=sys.stdout,
)
for _noisy in ('urllib3', 'httpx', 'httpcore', 'anthropic'):
    logging.getLogger(_noisy).setLevel(logging.WARNING)
log = logging.getLogger('scholarship_api')

from scholarship_research_agent_dynamic import DynamicScholarshipAgent
from research_opportunity_agent import ResearchOpportunityAgent
from scholarship_output_modules import (
    ExcelExporter, PDFExporter, HTMLDashboard,
    CalendarGenerator, ApplicationTracker
)
import claude_suggestions
import kv_store
import email_client
from dedupe import DuplicateFilter

# Claude suggestions are optional; past this the search returns database results only.
AI_SUGGESTIONS_TIMEOUT = 20

SCHOLARSHIP_FORMATS = {'csv', 'excel', 'pdf', 'calendar', 'tracker', 'html'}
RESEARCH_FORMATS = {'csv', 'excel', 'pdf', 'calendar', 'tracker'}


class BadRequest(Exception):
    """Client error whose message is safe to show the user (returned as 400)."""

app = Flask(__name__)
CORS(app)

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')


@app.before_request
def start_timer():
    g.start_time = time.perf_counter()


@app.after_request
def add_no_store_headers(response):
    """Search results depend on the current form payload; don't cache API responses."""
    if request.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-store, max-age=0'
        elapsed_ms = (time.perf_counter() - g.get('start_time', time.perf_counter())) * 1000
        log.info("%s %s -> %s (%.0f ms)", request.method, request.path, response.status_code, elapsed_ms)
    return response


@app.errorhandler(BadRequest)
def handle_bad_request(e):
    log.info("Bad request on %s: %s", request.path, e)
    return jsonify({'success': False, 'error': str(e)}), 400


@app.errorhandler(Exception)
def handle_unexpected_error(e):
    """Log the full traceback; never leak exception text to the client."""
    if isinstance(e, HTTPException):
        if not request.path.startswith('/api/'):
            return e
        return jsonify({'success': False, 'error': e.description}), e.code
    log.exception("Unhandled error on %s %s", request.method, request.path)
    return jsonify({
        'success': False,
        'error': 'Something went wrong on our end. Please try again in a moment.',
    }), 500


# ── Static file serving ────────────────────────────────────────────────────────

@app.route('/')
def serve_index():
    return send_from_directory(STATIC_DIR, 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory(STATIC_DIR, filename)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _clean_text(data: dict, key: str, default: str = '') -> str:
    value = data.get(key, default)
    if value is None:
        return default
    return str(value).strip() or default


def _json_body() -> dict:
    """Request JSON as a dict; malformed or non-object bodies are a 400."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise BadRequest('Request body must be a JSON object.')
    return data


def _require_valid(profile: dict):
    error = _profile_validation_error(profile)
    if error:
        raise BadRequest(error)


def _send_temp_file(filepath: str, mimetype: str, download_name: str):
    """Send a generated file from memory and delete it from /tmp, which persists
    (and fills up) across requests on a warm Vercel instance."""
    try:
        with open(filepath, 'rb') as f:
            payload = io.BytesIO(f.read())
    finally:
        try:
            os.remove(filepath)
        except OSError:
            log.warning("Could not remove temp file %s", filepath)
    return send_file(payload, mimetype=mimetype, as_attachment=True, download_name=download_name)


def _temp_path(filename: str) -> str:
    # Unique per request: second-resolution timestamps collide under concurrent downloads.
    return os.path.join(tempfile.gettempdir(), f"{uuid.uuid4().hex}_{filename}")


def _coerce_float(value, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _profile_validation_error(profile: dict) -> str:
    university = profile.get('university', '').strip()
    if not university or university.lower() in ('university', 'college', 'school', 'n/a', 'na'):
        return 'University name is required.'
    if len(university) < 3:
        return 'Please enter your full university name.'
    if not profile.get('major'):
        return 'Major is required.'
    if not profile.get('year'):
        return 'Year in school is required.'
    return ''


def _build_profile(data: dict) -> dict:
    data = data or {}
    return {
        'gpa': _coerce_float(data.get('gpa'), 3.5),
        'university': _clean_text(data, 'university'),
        'major': _clean_text(data, 'major'),
        'year': _clean_text(data, 'year'),
        'heritage': _clean_text(data, 'heritage', 'Not specified'),
        'gender': _clean_text(data, 'gender', 'Not specified'),
        'state': _clean_text(data, 'state', 'Not specified'),
        'residency': _clean_text(data, 'residency', 'Not specified'),
        'first_gen': data.get('first_gen', False),
        'military': data.get('military', False),
        'research': data.get('research', False),
        'discipline': _clean_text(data, 'discipline'),
        'skills': _clean_text(data, 'skills', 'Not specified'),
        'clubs': _clean_text(data, 'clubs', 'Not specified'),
        'athletics': _clean_text(data, 'athletics', 'Not specified'),
        'disability': _clean_text(data, 'disability', 'Not specified'),
        'email': 'Not specified',
    }


def _scholarship_to_dict(s) -> dict:
    return {
        'name': s.name,
        'amount_display': s.amount_display,
        'amount_min': s.amount_min,
        'amount_max': s.amount_max,
        'deadline': s.deadline,
        'days_until_deadline': s.days_until_deadline if s.days_until_deadline < 999 else 'TBD',
        'min_gpa': s.min_gpa,
        'recommended_gpa': s.recommended_gpa,
        'essay_required': s.essay_required,
        'essay_word_count': s.essay_word_count,
        'rec_letters_required': s.rec_letters_required,
        'interview_required': s.interview_required,
        'competitiveness': s.competitiveness,
        'category': s.category,
        'renewable': s.renewable,
        'estimated_hours': s.estimated_hours,
        'application_url': s.application_url,
        'notes': s.notes,
        'priority_score': s.priority_score,
        'source': 'Database',
    }


def _sort_dicts(items: list, sort_by: str) -> list:
    if sort_by == 'deadline':
        return sorted(items, key=lambda x: (
            x.get('days_until_deadline') if isinstance(x.get('days_until_deadline'), int) else 9999
        ))
    elif sort_by == 'amount':
        return sorted(items, key=lambda x: x.get('amount_max', 0), reverse=True)
    else:
        return sorted(items, key=lambda x: x.get('priority_score', 0), reverse=True)


def _run_agent(student_profile: dict, sort_by: str) -> list:
    """Run the local scholarship agent and return filtered, sorted dicts."""
    gpa = student_profile['gpa']
    agent = DynamicScholarshipAgent(
        user_gpa=gpa,
        home_state=student_profile.get('state', ''),
        discipline=student_profile.get('discipline', ''),
        student_profile=student_profile
    )
    agent.research_scholarships()

    if sort_by == 'deadline':
        raw = agent.sort_by_deadline()
    elif sort_by == 'amount':
        raw = agent.sort_by_amount()
    else:
        raw = agent.sort_by_priority()

    active = [s for s in raw if s.days_until_deadline >= 0]
    return [_scholarship_to_dict(s) for s in active], agent


# ── Search endpoint ────────────────────────────────────────────────────────────

@app.route('/api/search', methods=['POST'])
def search_scholarships():
    data = _json_body()
    student_profile = _build_profile(data)
    _require_valid(student_profile)
    sort_by = data.get('sort', 'priority')
    gpa = student_profile['gpa']

    # Run local agent
    scholarships_json, agent = _run_agent(student_profile, sort_by)

    external_results = _fetch_ai_suggestions(student_profile)

    # Deduplicate (prefer database entries). Names are compared fuzzily and
    # URLs by host+path, since Claude rarely spells a program exactly as the
    # catalog does ("The Barry M. Goldwater Scholarship" vs "Barry Goldwater Scholarship").
    seen = DuplicateFilter()
    for s in scholarships_json:
        seen.add(s['name'], s.get('application_url', ''))
    added = 0
    for ext in external_results:
        name = ext.get('name', '')
        url = ext.get('application_url', '')
        if seen.is_duplicate(name, url):
            log.debug("Dropping AI suggestion already in results: %r", name)
            continue
        seen.add(name, url)
        scholarships_json.append(ext)
        added += 1

    # Re-sort combined list
    scholarships_json = _sort_dicts(scholarships_json, sort_by)

    # Stats
    gpa_eligible = [s for s in scholarships_json if s.get('min_gpa', 0) <= gpa]
    urgent = [s for s in scholarships_json
              if isinstance(s.get('days_until_deadline'), int)
              and 0 < s['days_until_deadline'] <= 30]
    total_potential = sum(
        (s.get('amount_min', 0) + s.get('amount_max', 0)) / 2
        for s in scholarships_json
    )

    stats = {
        'total_scholarships': len(scholarships_json),
        'gpa_eligible': len(gpa_eligible),
        'urgent_deadlines_30_days': len(urgent),
        'total_potential_award': f"${total_potential:,.0f}",
        'sources': {
            'database': sum(1 for s in scholarships_json if s.get('source') == 'Database'),
            'ai_suggested': sum(1 for s in scholarships_json if s.get('source') == 'AI Suggested'),
        }
    }

    log.info("Scholarship search: major=%r year=%r -> %d results (%d database, %d of %d AI suggestions kept)",
             student_profile['major'], student_profile['year'], len(scholarships_json),
             stats['sources']['database'], added, len(external_results))

    return jsonify({
        'success': True,
        'profile': student_profile,
        'stats': stats,
        'scholarships': scholarships_json,
        'total': len(scholarships_json)
    })


def _fetch_ai_suggestions(student_profile: dict) -> list:
    """Claude suggestions, or [] if unavailable, failing, or slower than the timeout."""
    if not claude_suggestions.is_available():
        return []
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(claude_suggestions.get_suggestions, student_profile)
    try:
        return future.result(timeout=AI_SUGGESTIONS_TIMEOUT)
    except FuturesTimeout:
        log.warning("Claude suggestions timed out after %ss; returning database results only",
                    AI_SUGGESTIONS_TIMEOUT)
        return []
    except Exception:
        log.exception("Claude suggestions failed; returning database results only")
        return []
    finally:
        # Don't block the response waiting on a slow API call.
        executor.shutdown(wait=False, cancel_futures=True)


# ── Download endpoint ──────────────────────────────────────────────────────────

@app.route('/api/download/<format_type>', methods=['POST'])
def download_file(format_type):
    if format_type not in SCHOLARSHIP_FORMATS:
        raise BadRequest('Invalid format type')
    data = _json_body()
    student_profile = _build_profile(data)
    _require_valid(student_profile)
    sort_by = data.get('sort', 'priority')
    gpa = student_profile['gpa']

    _, agent = _run_agent(student_profile, sort_by)

    if sort_by == 'deadline':
        scholarships = agent.sort_by_deadline()
    elif sort_by == 'amount':
        scholarships = agent.sort_by_amount()
    else:
        scholarships = agent.sort_by_priority()

    scholarships = [s for s in scholarships if s.days_until_deadline >= 0]

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    if format_type == 'csv':
        filename = f'scholarships_{timestamp}.csv'
        filepath = _temp_path(filename)
        agent.export_to_csv(filepath, sort_by)
        mimetype = 'text/csv'

    elif format_type == 'excel':
        excel_exporter = ExcelExporter()
        if not excel_exporter.available:
            log.error("Excel export requested but openpyxl is not installed")
            return jsonify({'success': False, 'error': 'Excel export not available'}), 500
        filename = f'scholarships_{timestamp}.xlsx'
        filepath = _temp_path(filename)
        excel_exporter.export(scholarships, filepath, student_profile)
        mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

    elif format_type == 'pdf':
        pdf_exporter = PDFExporter()
        if not pdf_exporter.available:
            log.error("PDF export requested but reportlab is not installed")
            return jsonify({'success': False, 'error': 'PDF export not available'}), 500
        filename = f'scholarships_{timestamp}.pdf'
        filepath = _temp_path(filename)
        pdf_exporter.export(scholarships, filepath, gpa, student_profile)
        mimetype = 'application/pdf'

    elif format_type == 'calendar':
        calendar_gen = CalendarGenerator()
        filename = f'scholarships_{timestamp}.ics'
        filepath = _temp_path(filename)
        calendar_gen.export(scholarships, filepath)
        mimetype = 'text/calendar'

    elif format_type == 'tracker':
        tracker = ApplicationTracker()
        filename = f'scholarship_tracker_{timestamp}.csv'
        filepath = _temp_path(filename)
        tracker.create_tracker(scholarships, filepath)
        mimetype = 'text/csv'

    else:  # html
        html_dashboard = HTMLDashboard()
        stats = agent.generate_summary_stats()
        filename = f'scholarships_{timestamp}.html'
        filepath = _temp_path(filename)
        html_dashboard.export(scholarships, filepath, stats, student_profile)
        mimetype = 'text/html'

    log.info("Scholarship export: format=%s rows=%d", format_type, len(scholarships))
    return _send_temp_file(filepath, mimetype, filename)


# ── Research opportunity endpoints ─────────────────────────────────────────────

def _build_research_profile(data: dict) -> dict:
    """Profile shape consumed by ResearchOpportunityAgent."""
    data = data or {}
    return {
        'gpa': _coerce_float(data.get('gpa'), 3.0),
        'university': _clean_text(data, 'university'),
        'major': _clean_text(data, 'major'),
        'year': _clean_text(data, 'year'),
        'discipline': _clean_text(data, 'discipline'),
        'state': _clean_text(data, 'state'),
        'heritage': _clean_text(data, 'heritage'),
        'gender': _clean_text(data, 'gender'),
        'residency': _clean_text(data, 'residency'),
        'first_gen': bool(data.get('first_gen', False)),
        'military': bool(data.get('military', False)),
        'disability': _clean_text(data, 'disability'),
        'skills': _clean_text(data, 'skills'),
        'clubs': _clean_text(data, 'clubs'),
        'athletics': _clean_text(data, 'athletics'),
    }


def _opportunity_to_dict(o) -> dict:
    return {
        'name': o.name,
        'organization': o.organization,
        'research_area': o.research_area,
        'location': o.location,
        'compensation_type': o.compensation_type,
        'stipend_amount': o.stipend_amount,
        'stipend_display': f"${o.stipend_amount:,}" if o.stipend_amount > 0 else o.compensation_type,
        'duration': o.duration,
        'deadline': o.deadline,
        'days_until_deadline': getattr(o, 'days_until_deadline', 999),
        'gpa_min': o.gpa_min,
        'gpa_preferred': o.gpa_preferred,
        'eligible_years': o.eligible_years,
        'majors': o.majors,
        'description': o.description,
        'application_url': o.application_url,
        'application_tips': o.application_tips,
        'housing_provided': o.housing_provided,
        'travel_covered': o.travel_covered,
        'category': o.category,
        'competitiveness': o.competitiveness,
        'priority_score': o.priority_score,
    }


@app.route('/api/research', methods=['POST'])
def search_research():
    """Search research opportunities based on student profile."""
    data = _json_body()
    student_profile = _build_research_profile(data)
    _require_valid(student_profile)

    agent = ResearchOpportunityAgent(student_profile)
    opportunities = agent.research_opportunities()

    opportunities_json = [_opportunity_to_dict(o) for o in opportunities]

    total_paid = sum(1 for o in opportunities if o.stipend_amount > 0)
    avg_stipend = (
        sum(o.stipend_amount for o in opportunities if o.stipend_amount > 0)
        / total_paid
    ) if total_paid else 0
    with_housing = sum(1 for o in opportunities if o.housing_provided)

    stats = {
        'total_opportunities': len(opportunities),
        'paid_opportunities': total_paid,
        'average_stipend': f"${avg_stipend:,.0f}",
        'with_housing': with_housing,
        'categories': sorted({o.category for o in opportunities}),
    }

    log.info("Research search: major=%r year=%r -> %d results",
             student_profile['major'], student_profile['year'], len(opportunities_json))

    return jsonify({
        'success': True,
        'profile': student_profile,
        'stats': stats,
        'opportunities': opportunities_json,
        'total': len(opportunities_json),
    })


def _research_to_rows(opportunities):
    headers = [
        'Priority', 'Name', 'Organization', 'Category', 'Research Area',
        'Location', 'Compensation', 'Stipend', 'Duration', 'Deadline',
        'GPA Min', 'GPA Preferred', 'Eligible Years', 'Majors',
        'Housing', 'Travel Covered', 'Competitiveness',
        'Description', 'Application Tips', 'Application URL',
    ]
    rows = []
    for o in opportunities:
        rows.append([
            o.priority_score, o.name, o.organization, o.category, o.research_area,
            o.location, o.compensation_type,
            f"${o.stipend_amount:,}" if o.stipend_amount > 0 else "Unpaid",
            o.duration, o.deadline,
            o.gpa_min, o.gpa_preferred,
            ", ".join(o.eligible_years) if o.eligible_years else "Any",
            ", ".join(o.majors) if o.majors else "Any",
            "Yes" if o.housing_provided else "No",
            "Yes" if o.travel_covered else "No",
            o.competitiveness,
            o.description, o.application_tips, o.application_url,
        ])
    return headers, rows


def _research_export_csv(opportunities, filepath):
    import csv
    headers, rows = _research_to_rows(opportunities)
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)


def _research_export_excel(opportunities, filepath, student_profile):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment

    wb = Workbook()
    ws = wb.active
    ws.title = "Research Opportunities"

    ws['A1'] = f"Research Opportunities — {student_profile.get('major', 'Student')}"
    ws['A1'].font = Font(size=14, bold=True, color='FFFFFF')
    ws['A1'].fill = PatternFill(start_color='5B21B6', end_color='5B21B6', fill_type='solid')
    ws.merge_cells('A1:T1')
    ws['A1'].alignment = Alignment(horizontal='center', vertical='center')

    headers, rows = _research_to_rows(opportunities)
    header_fill = PatternFill(start_color='8B5CF6', end_color='8B5CF6', fill_type='solid')
    header_font = Font(bold=True, color='FFFFFF')

    for col_idx, h in enumerate(headers, start=1):
        c = ws.cell(row=3, column=col_idx, value=h)
        c.font = header_font
        c.fill = header_fill
        c.alignment = Alignment(horizontal='center')

    for row_idx, row in enumerate(rows, start=4):
        for col_idx, value in enumerate(row, start=1):
            ws.cell(row=row_idx, column=col_idx, value=value)

    for col_idx, h in enumerate(headers, start=1):
        ws.column_dimensions[ws.cell(row=3, column=col_idx).column_letter].width = max(14, min(50, len(h) + 4))

    wb.save(filepath)


def _research_export_pdf(opportunities, filepath, student_profile):
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

    doc = SimpleDocTemplate(filepath, pagesize=letter,
                            leftMargin=0.5 * inch, rightMargin=0.5 * inch,
                            topMargin=0.5 * inch, bottomMargin=0.5 * inch)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('title', parent=styles['Heading1'], textColor=colors.HexColor('#5B21B6'))
    story = [
        Paragraph("Research Opportunities Report", title_style),
        Paragraph(f"Student: {student_profile.get('major', '')} at "
                  f"{student_profile.get('university', '')} — GPA {student_profile.get('gpa', '')}",
                  styles['Normal']),
        Spacer(1, 12),
    ]

    for o in opportunities:
        story.append(Paragraph(f"<b>{o.name}</b> — Priority {o.priority_score}", styles['Heading2']))
        meta = [
            ['Organization', o.organization],
            ['Category', o.category],
            ['Research Area', o.research_area],
            ['Location', o.location],
            ['Compensation', f"{o.compensation_type} (${o.stipend_amount:,})" if o.stipend_amount else o.compensation_type],
            ['Duration', o.duration],
            ['Deadline', o.deadline],
            ['GPA Required', f"{o.gpa_min}+ (preferred {o.gpa_preferred})"],
            ['Eligible Years', ", ".join(o.eligible_years) if o.eligible_years else "Any"],
            ['Competitiveness', o.competitiveness],
            ['Housing', 'Yes' if o.housing_provided else 'No'],
            ['Travel Covered', 'Yes' if o.travel_covered else 'No'],
        ]
        t = Table(meta, colWidths=[1.6 * inch, 5.4 * inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#EDE9FE')),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#D4D4D8')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
        ]))
        story.append(t)
        story.append(Spacer(1, 6))
        story.append(Paragraph(f"<b>Description:</b> {o.description}", styles['Normal']))
        story.append(Paragraph(f"<b>Application Tips:</b> {o.application_tips}", styles['Normal']))
        story.append(Paragraph(f"<b>Apply:</b> <link href='{o.application_url}'>{o.application_url}</link>", styles['Normal']))
        story.append(Spacer(1, 14))

    doc.build(story)


def _research_export_calendar(opportunities, filepath):
    """ICS file with VTODO entries (deadlines are free-text strings)."""
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Tim Smith//Research Opportunity Tracker//EN",
    ]
    now = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    for i, o in enumerate(opportunities):
        lines.extend([
            "BEGIN:VTODO",
            f"UID:research-{i}-{now}@tsprofits",
            f"DTSTAMP:{now}",
            f"SUMMARY:{o.name} ({o.organization})",
            f"DESCRIPTION:{o.description}\\nDeadline: {o.deadline}\\nStipend: ${o.stipend_amount}\\nApply: {o.application_url}",
            "STATUS:NEEDS-ACTION",
            "END:VTODO",
        ])
    lines.append("END:VCALENDAR")
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write("\r\n".join(lines))


def _research_export_tracker(opportunities, filepath):
    import csv
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'Status', 'Name', 'Organization', 'Deadline', 'Stipend',
            'Application URL', 'Materials Needed', 'Notes', 'Date Applied', 'Result'
        ])
        for o in opportunities:
            writer.writerow([
                'Not Started', o.name, o.organization, o.deadline,
                f"${o.stipend_amount:,}" if o.stipend_amount else "Unpaid",
                o.application_url,
                'Resume, Personal Statement, Transcript, 2-3 Recommendations',
                o.application_tips,
                '', '',
            ])


@app.route('/api/research/download/<format_type>', methods=['POST'])
def download_research(format_type):
    """Generate and download research opportunity files."""
    if format_type not in RESEARCH_FORMATS:
        raise BadRequest('Invalid format type')
    data = _json_body()
    student_profile = _build_research_profile(data)
    _require_valid(student_profile)

    agent = ResearchOpportunityAgent(student_profile)
    opportunities = agent.research_opportunities()

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    if format_type == 'csv':
        filename = f'research_opportunities_{timestamp}.csv'
        filepath = _temp_path(filename)
        _research_export_csv(opportunities, filepath)
        mimetype = 'text/csv'
    elif format_type == 'excel':
        try:
            import openpyxl  # noqa: F401
        except ImportError:
            log.error("Research Excel export requested but openpyxl is not installed")
            return jsonify({'success': False, 'error': 'Excel export requires openpyxl'}), 500
        filename = f'research_opportunities_{timestamp}.xlsx'
        filepath = _temp_path(filename)
        _research_export_excel(opportunities, filepath, student_profile)
        mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    elif format_type == 'pdf':
        try:
            import reportlab  # noqa: F401
        except ImportError:
            log.error("Research PDF export requested but reportlab is not installed")
            return jsonify({'success': False, 'error': 'PDF export requires reportlab'}), 500
        filename = f'research_opportunities_{timestamp}.pdf'
        filepath = _temp_path(filename)
        _research_export_pdf(opportunities, filepath, student_profile)
        mimetype = 'application/pdf'
    elif format_type == 'calendar':
        filename = f'research_deadlines_{timestamp}.ics'
        filepath = _temp_path(filename)
        _research_export_calendar(opportunities, filepath)
        mimetype = 'text/calendar'
    else:  # tracker
        filename = f'research_tracker_{timestamp}.csv'
        filepath = _temp_path(filename)
        _research_export_tracker(opportunities, filepath)
        mimetype = 'text/csv'

    log.info("Research export: format=%s rows=%d", format_type, len(opportunities))
    return _send_temp_file(filepath, mimetype, filename)


# ── Email alert endpoints ──────────────────────────────────────────────────────

@app.route('/api/subscribe', methods=['POST'])
def subscribe():
    data = _json_body()
    to_email = (data.get('email') or '').strip().lower()
    profile = data.get('profile') or {}
    if not isinstance(profile, dict):
        raise BadRequest('Profile must be an object.')

    if not to_email or '@' not in to_email:
        raise BadRequest('Valid email required')

    if not kv_store.is_available() and not email_client.is_available():
        log.warning("Subscribe attempted but neither KV storage nor email is configured")
        return jsonify({'success': False, 'error': 'Email alerts are not available yet. Check back soon!'}), 503

    stored = kv_store.save_subscriber(to_email, profile)
    sent = email_client.send_confirmation(to_email, profile)
    log.info("Subscribe: stored=%s confirmation_sent=%s", stored, sent)

    if not stored and not sent:
        return jsonify({'success': False, 'error': 'Could not save subscription. Please try again.'}), 500

    return jsonify({
        'success': True,
        'stored': stored,
        'email_sent': sent,
    })


@app.route('/api/unsubscribe', methods=['GET'])
def unsubscribe():
    to_email = request.args.get('email', '').strip().lower()
    if to_email and not kv_store.unsubscribe(to_email):
        log.warning("Unsubscribe could not remove subscriber from KV")
    return '''<html><body style="font-family:sans-serif;text-align:center;padding:60px">
        <h2>✅ Unsubscribed</h2>
        <p>You've been removed from weekly scholarship alerts.</p>
        <a href="/">Return to Scholarship Search</a>
    </body></html>'''


@app.route('/api/cron', methods=['GET'])
def run_cron():
    """Weekly cron job — sends scholarship alerts to all subscribers.
    Secured by CRON_SECRET env var; called by Vercel cron schedule."""
    auth = request.headers.get('Authorization', '')
    cron_secret = os.environ.get('CRON_SECRET', '')
    if cron_secret and auth != f'Bearer {cron_secret}':
        log.warning("Rejected unauthorized cron request")
        return jsonify({'error': 'Unauthorized'}), 401

    subscribers = kv_store.get_all_subscribers()
    log.info("Cron: sending weekly alerts to %d subscribers", len(subscribers))
    sent_count = 0
    errors = []

    for sub in subscribers:
        to_email = sub['email']
        try:
            # Stored profiles come straight from the browser; normalize them the
            # same way /api/search does so missing keys can't crash the agent.
            profile = _build_profile(sub['profile'] if isinstance(sub['profile'], dict) else {})
            if _profile_validation_error(profile):
                errors.append(f"{to_email}: incomplete saved profile")
                continue
            scholarships_json, _ = _run_agent(profile, 'priority')
            if email_client.send_weekly_alert(to_email, scholarships_json, profile):
                sent_count += 1
            elif scholarships_json:
                errors.append(f"{to_email}: email send failed")
        except Exception:
            log.exception("Cron: weekly alert failed for a subscriber")
            errors.append(f"{to_email}: unexpected error")

    log.info("Cron finished: %d sent, %d errors", sent_count, len(errors))
    return jsonify({'success': True, 'sent': sent_count, 'errors': errors})


if __name__ == '__main__':
    app.run(debug=True, port=int(os.environ.get('PORT', 5000)))

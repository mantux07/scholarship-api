#!/usr/bin/env python3
"""
Author: Tim Smith
Note: All Code owned by Tim

Flask API Backend for Scholarship Research Web App
"""

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import sys
import os
import tempfile
from datetime import datetime

# Add parent directory to path to import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import dynamic scholarship agent
from scholarship_research_agent_dynamic import DynamicScholarshipAgent
from scholarship_output_modules import (
    ExcelExporter, PDFExporter, HTMLDashboard,
    CalendarGenerator, ApplicationTracker
)

app = Flask(__name__)
CORS(app)  # Enable CORS for cross-origin requests from your website

@app.route('/')
def home():
    """Health check endpoint"""
    return jsonify({
        'status': 'online',
        'service': 'Scholarship Research API',
        'version': '1.0',
        'endpoints': {
            '/api/search': 'POST - Search scholarships',
            '/api/download': 'POST - Download results file'
        }
    })

@app.route('/api/search', methods=['POST'])
def search_scholarships():
    """Search scholarships based on student profile"""
    try:
        # Get student profile from request
        data = request.json

        # Extract parameters with defaults
        gpa = float(data.get('gpa', 3.5))
        university = data.get('university', 'University')
        major = data.get('major', 'Engineering')
        year = data.get('year', 'Sophomore')
        heritage = data.get('heritage', '')
        gender = data.get('gender', '')
        state = data.get('state', '')
        residency = data.get('residency', '')
        first_gen = data.get('first_gen', False)
        military = data.get('military', False)
        discipline = data.get('discipline', '')
        skills = data.get('skills', '')
        clubs = data.get('clubs', '')
        athletics = data.get('athletics', '')
        sort_by = data.get('sort', 'priority')

        # Create student profile
        student_profile = {
            'gpa': gpa,
            'university': university,
            'major': major,
            'year': year,
            'heritage': heritage or 'Not specified',
            'gender': gender or 'Not specified',
            'state': state or 'Not specified',
            'residency': residency or 'Not specified',
            'first_gen': first_gen,
            'military': military,
            'discipline': discipline or 'General',
            'skills': skills or 'Not specified',
            'clubs': clubs or 'Not specified',
            'athletics': athletics or 'Not specified',
            'email': 'Not specified'
        }

        # Initialize agent and search
        agent = DynamicScholarshipAgent(
            user_gpa=gpa,
            home_state=state,
            discipline=discipline,
            student_profile=student_profile
        )
        agent.research_scholarships()

        # Sort results
        if sort_by == 'deadline':
            scholarships = agent.sort_by_deadline()
        elif sort_by == 'amount':
            scholarships = agent.sort_by_amount()
        else:
            scholarships = agent.sort_by_priority()

        # No filtering - show all scholarships
        # User can review and decide what applies to them
        pass

        # Generate statistics for filtered scholarships
        gpa_eligible = [s for s in scholarships if s.min_gpa <= gpa]
        urgent = [s for s in scholarships if s.days_until_deadline <= 30 and s.days_until_deadline > 0]
        total_potential = sum((s.amount_min + s.amount_max) / 2 for s in scholarships)

        stats = {
            'total_scholarships': len(scholarships),
            'gpa_eligible': len(gpa_eligible),
            'urgent_deadlines_30_days': len(urgent),
            'total_potential_award': f"${total_potential:,.0f}",
            'average_priority': sum(s.priority_score for s in scholarships) / len(scholarships) if scholarships else 0
        }

        # Convert scholarships to JSON-serializable format
        scholarships_json = []
        for s in scholarships:
            scholarships_json.append({
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
                'priority_score': s.priority_score
            })

        return jsonify({
            'success': True,
            'profile': student_profile,
            'stats': stats,
            'scholarships': scholarships_json,
            'total': len(scholarships_json)
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/download/<format_type>', methods=['POST'])
def download_file(format_type):
    """Generate and download scholarship files"""
    try:
        data = request.json

        # Recreate the search (we need the scholarship objects)
        gpa = float(data.get('gpa', 3.5))
        state = data.get('state', '')
        discipline = data.get('discipline', '')
        sort_by = data.get('sort', 'priority')

        student_profile = {
            'gpa': gpa,
            'university': data.get('university', 'University'),
            'major': data.get('major', 'Engineering'),
            'year': data.get('year', 'Sophomore'),
            'heritage': data.get('heritage', '') or 'Not specified',
            'gender': data.get('gender', '') or 'Not specified',
            'state': state or 'Not specified',
            'residency': data.get('residency', '') or 'Not specified',
            'first_gen': data.get('first_gen', False),
            'military': data.get('military', False),
            'discipline': discipline or 'General',
            'skills': data.get('skills', '') or 'Not specified',
            'clubs': data.get('clubs', '') or 'Not specified',
            'athletics': data.get('athletics', '') or 'Not specified',
            'email': 'Not specified'
        }

        agent = DynamicScholarshipAgent(
            user_gpa=gpa,
            home_state=state,
            discipline=discipline,
            student_profile=student_profile
        )
        agent.research_scholarships()

        if sort_by == 'deadline':
            scholarships = agent.sort_by_deadline()
        elif sort_by == 'amount':
            scholarships = agent.sort_by_amount()
        else:
            scholarships = agent.sort_by_priority()

        # No filtering - show all scholarships
        pass

        # Generate temp file
        temp_dir = tempfile.gettempdir()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        if format_type == 'csv':
            filename = f'scholarships_{timestamp}.csv'
            filepath = os.path.join(temp_dir, filename)
            agent.export_to_csv(filepath, sort_by)
            mimetype = 'text/csv'

        elif format_type == 'excel':
            excel_exporter = ExcelExporter()
            if not excel_exporter.available:
                return jsonify({'success': False, 'error': 'Excel export not available'}), 500
            filename = f'scholarships_{timestamp}.xlsx'
            filepath = os.path.join(temp_dir, filename)
            excel_exporter.export(scholarships, filepath, student_profile)
            mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

        elif format_type == 'pdf':
            pdf_exporter = PDFExporter()
            if not pdf_exporter.available:
                return jsonify({'success': False, 'error': 'PDF export not available'}), 500
            filename = f'scholarships_{timestamp}.pdf'
            filepath = os.path.join(temp_dir, filename)
            pdf_exporter.export(scholarships, filepath, gpa, student_profile)
            mimetype = 'application/pdf'

        elif format_type == 'calendar':
            calendar_gen = CalendarGenerator()
            filename = f'scholarships_{timestamp}.ics'
            filepath = os.path.join(temp_dir, filename)
            calendar_gen.export(scholarships, filepath)
            mimetype = 'text/calendar'

        elif format_type == 'tracker':
            tracker = ApplicationTracker()
            filename = f'scholarship_tracker_{timestamp}.csv'
            filepath = os.path.join(temp_dir, filename)
            tracker.create_tracker(scholarships, filepath)
            mimetype = 'text/csv'

        elif format_type == 'html':
            html_dashboard = HTMLDashboard()
            stats = agent.generate_summary_stats()
            filename = f'scholarships_{timestamp}.html'
            filepath = os.path.join(temp_dir, filename)
            html_dashboard.export(scholarships, filepath, stats, student_profile)
            mimetype = 'text/html'

        else:
            return jsonify({'success': False, 'error': 'Invalid format type'}), 400

        return send_file(
            filepath,
            mimetype=mimetype,
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    # Development server - using port 8080 to avoid macOS AirPlay port conflicts
    app.run(debug=True, host='0.0.0.0', port=8083)

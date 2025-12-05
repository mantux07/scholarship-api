#!/usr/bin/env python3
"""
Author: Tim Smith
Note: All Code owned by Tim

Dynamic Scholarship Research Agent - Profile-Based Search
Generates relevant scholarships based on student profile inputs
"""

import csv
import json
import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict

# Add webapp directory to path for database loader import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'webapp'))

# Import scholarship database loader if available
try:
    from scholarship_database_loader import ScholarshipDatabase
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False
    print("⚠️  Database loader not available, using hardcoded scholarships only")

@dataclass
class Scholarship:
    """Enhanced scholarship data structure"""
    name: str
    amount_min: int
    amount_max: int
    amount_display: str
    deadline: str
    deadline_date: Optional[datetime]
    min_gpa: float
    recommended_gpa: float
    eligibility: str
    essay_required: bool
    essay_word_count: int
    rec_letters_required: int
    interview_required: bool
    competitiveness: str  # Low, Medium, High, Very High
    application_url: str
    notes: str
    renewable: bool
    category: str
    estimated_hours: float
    priority_score: float = 0.0
    days_until_deadline: int = 999
    date_researched: str = ""

    def is_expired(self) -> bool:
        """Check if scholarship deadline has passed"""
        if not self.deadline_date:
            return False  # Keep rolling/varies deadlines

        if self.deadline.lower() in ['rolling', 'varies', 'multiple deadlines', 'ongoing']:
            return False

        return datetime.now() > self.deadline_date

    def get_urgency_level(self) -> str:
        """Return urgency level: critical, high, medium, low, none"""
        if not self.deadline_date or self.deadline.lower() in ['rolling', 'varies', 'multiple deadlines', 'ongoing']:
            return "none"

        if self.days_until_deadline <= 0:
            return "expired"
        elif self.days_until_deadline < 7:
            return "critical"
        elif self.days_until_deadline < 30:
            return "high"
        elif self.days_until_deadline < 90:
            return "medium"
        else:
            return "low"

    def to_dict(self) -> dict:
        """Convert scholarship to dictionary for JSON serialization"""
        return {
            'name': self.name,
            'amount_min': self.amount_min,
            'amount_max': self.amount_max,
            'amount_display': self.amount_display,
            'deadline': self.deadline,
            'deadline_date': self.deadline_date.strftime("%Y-%m-%d") if self.deadline_date else None,
            'days_until_deadline': self.days_until_deadline,
            'urgency_level': self.get_urgency_level(),
            'min_gpa': self.min_gpa,
            'recommended_gpa': self.recommended_gpa,
            'eligibility': self.eligibility,
            'essay_required': self.essay_required,
            'essay_word_count': self.essay_word_count,
            'rec_letters_required': self.rec_letters_required,
            'interview_required': self.interview_required,
            'competitiveness': self.competitiveness,
            'application_url': self.application_url,
            'notes': self.notes,
            'renewable': self.renewable,
            'category': self.category,
            'estimated_hours': self.estimated_hours,
            'priority_score': self.priority_score
        }

class DynamicScholarshipAgent:
    """Dynamic scholarship search based on student profile"""

    def __init__(self, user_gpa: float = 3.5, home_state: str = "", discipline: str = "", student_profile: dict = None):
        self.scholarships: List[Scholarship] = []
        self.user_gpa = user_gpa
        self.home_state = home_state
        self.discipline = discipline
        self.student_profile = student_profile or {}

        # Extract profile details
        self.university = self.student_profile.get('university', 'University')
        self.major = self.student_profile.get('major', 'Engineering')
        self.year = self.student_profile.get('year', 'Sophomore')
        self.heritage = self.student_profile.get('heritage', 'Not specified')
        self.gender = self.student_profile.get('gender', 'Not specified')
        self.state = self.student_profile.get('state', home_state or 'Not specified')
        self.residency = self.student_profile.get('residency', 'Not specified')
        self.first_gen = self.student_profile.get('first_gen', False)
        self.military = self.student_profile.get('military', False)
        self.disability = self.student_profile.get('disability', '')
        self.skills = self.student_profile.get('skills', '')
        self.clubs = self.student_profile.get('clubs', '')
        self.athletics = self.student_profile.get('athletics', '')

        self.today = datetime.now()

    def parse_deadline(self, deadline_str: str) -> Optional[datetime]:
        """Parse deadline string to datetime object"""
        try:
            formats = [
                '%B %d, %Y', '%b %d, %Y',
                '%m/%d/%Y', '%Y-%m-%d',
                '%B %Y', '%b %Y'
            ]
            for fmt in formats:
                try:
                    return datetime.strptime(deadline_str, fmt)
                except ValueError:
                    continue

            # Try month/year parsing
            if '2026' in deadline_str:
                month_map = {
                    'January': 1, 'February': 2, 'March': 3, 'April': 4,
                    'May': 5, 'June': 6, 'July': 7, 'August': 8,
                    'September': 9, 'October': 10, 'November': 11, 'December': 12
                }
                for month, num in month_map.items():
                    if month in deadline_str:
                        return datetime(2026, num, 1)
            elif '2025' in deadline_str:
                month_map = {
                    'December': 12, 'November': 11, 'October': 10
                }
                for month, num in month_map.items():
                    if month in deadline_str:
                        return datetime(2025, num, 1)
        except:
            pass
        return None

    def calculate_priority_score(self, scholarship: Scholarship) -> float:
        """Calculate priority score based on award amount, deadline, GPA, and competitiveness"""
        score = 0.0

        # Award amount score (0-40 points)
        avg_amount = (scholarship.amount_min + scholarship.amount_max) / 2
        if avg_amount >= 10000:
            score += 40
        elif avg_amount >= 5000:
            score += 30
        elif avg_amount >= 2000:
            score += 20
        else:
            score += 10

        # Deadline urgency (0-30 points)
        if scholarship.days_until_deadline <= 30:
            score += 30
        elif scholarship.days_until_deadline <= 60:
            score += 25
        elif scholarship.days_until_deadline <= 90:
            score += 20
        elif scholarship.days_until_deadline <= 180:
            score += 15
        else:
            score += 10

        # GPA match (0-20 points)
        if self.user_gpa >= scholarship.recommended_gpa:
            score += 20
        elif self.user_gpa >= scholarship.min_gpa:
            score += 15
        else:
            score += 5

        # Competitiveness (0-10 points)
        comp_scores = {'Low': 10, 'Medium': 7, 'High': 5, 'Very High': 3}
        score += comp_scores.get(scholarship.competitiveness, 5)

        return round(score, 2)

    def is_stem_major(self) -> bool:
        """Check if student's major is STEM-related"""
        major_lower = self.major.lower()
        return any(word in major_lower for word in [
            'engineering', 'computer', 'science', 'technology', 'math',
            'physics', 'chemistry', 'biology', 'data', 'statistics'
        ])

    def is_business_major(self) -> bool:
        """Check if student's major is business-related"""
        major_lower = self.major.lower()
        return any(word in major_lower for word in [
            'business', 'accounting', 'finance', 'economics',
            'management', 'marketing', 'entrepreneur'
        ])

    def is_health_major(self) -> bool:
        """Check if student's major is health/medical-related"""
        major_lower = self.major.lower()
        return any(word in major_lower for word in [
            'pre-med', 'premed', 'nursing', 'health', 'medical',
            'pharmacy', 'dental', 'veterinary', 'biology', 'biochemistry'
        ])

    def is_arts_humanities_major(self) -> bool:
        """Check if student's major is arts/humanities-related"""
        major_lower = self.major.lower()
        return any(word in major_lower for word in [
            'art', 'music', 'literature', 'history', 'english',
            'language', 'philosophy', 'psychology', 'sociology'
        ])

    def load_scholarships_from_database(self):
        """Load scholarships from JSON database"""
        if not DATABASE_AVAILABLE:
            return

        try:
            # Try to find the database file
            # Check both webapp directory and parent directory
            possible_paths = [
                os.path.join(os.path.dirname(__file__), '..', 'webapp', 'scholarship_database.json'),
                os.path.join(os.path.dirname(__file__), 'scholarship_database.json'),
                'scholarship_database.json'
            ]

            db_path = None
            for path in possible_paths:
                if os.path.exists(path):
                    db_path = path
                    break

            if not db_path:
                print("⚠️  scholarship_database.json not found, skipping database load")
                return

            # Load database
            db = ScholarshipDatabase(db_path)

            # Filter scholarships by student profile
            db_scholarships = db.get_scholarships_for_profile(self.student_profile)

            print(f"✓ Loading {len(db_scholarships)} scholarship(s) from database (filtered by profile)")

            # Convert database scholarships to Scholarship objects
            for s in db_scholarships:
                # Map database fields to add_scholarship parameters
                details = s.get('details', {})
                requirements = s.get('requirements', {})

                # Build eligibility string from requirements
                eligibility_parts = []
                if requirements:
                    if 'heritage' in requirements:
                        eligibility_parts.append(f"Heritage: {', '.join(requirements['heritage'])}")
                    if 'major' in requirements:
                        eligibility_parts.append(f"Major: {', '.join(requirements['major'])}")
                    if 'citizenship' in requirements:
                        eligibility_parts.append(f"Citizenship: {', '.join(requirements['citizenship'])}")

                eligibility = "; ".join(eligibility_parts) if eligibility_parts else details.get('description', '')

                # Add the scholarship
                self.add_scholarship(
                    name=s.get('name'),
                    amount_min=s.get('amount_min', 0),
                    amount_max=s.get('amount_max', 0),
                    amount_display=s.get('amount_display', '$0'),
                    deadline=s.get('deadline', 'Rolling'),
                    min_gpa=s.get('gpa_min', 0.0),
                    recommended_gpa=s.get('gpa_preferred', s.get('gpa_min', 0.0)),
                    eligibility=eligibility,
                    essay_required=details.get('essay_required', False),
                    essay_word_count=details.get('essay_word_count', 0),
                    rec_letters_required=details.get('letters_required', 0),
                    interview_required=details.get('interview_required', False),
                    competitiveness=details.get('competitiveness', 'Medium'),
                    application_url=s.get('application_url', s.get('source_url', '')),
                    notes=s.get('notes', ''),
                    renewable=s.get('deadline_type') == 'annual',
                    category=s.get('category', 'General'),
                    estimated_hours=details.get('estimated_hours', 3.0)
                )

            print(f"✓ Successfully loaded database scholarships")

        except Exception as e:
            print(f"⚠️  Error loading database: {e}")
            # Continue with hardcoded scholarships even if database fails

    def add_scholarship(self, name: str, amount_min: int, amount_max: int,
                       amount_display: str, deadline: str, min_gpa: float,
                       recommended_gpa: float, eligibility: str,
                       essay_required: bool, essay_word_count: int,
                       rec_letters_required: int, interview_required: bool,
                       competitiveness: str, application_url: str,
                       notes: str, renewable: bool, category: str,
                       estimated_hours: float):
        """Add scholarship with metadata"""

        deadline_date = self.parse_deadline(deadline)
        days_until = 999
        if deadline_date:
            days_until = (deadline_date - self.today).days

        scholarship = Scholarship(
            name=name,
            amount_min=amount_min,
            amount_max=amount_max,
            amount_display=amount_display,
            deadline=deadline,
            deadline_date=deadline_date,
            min_gpa=min_gpa,
            recommended_gpa=recommended_gpa,
            eligibility=eligibility,
            essay_required=essay_required,
            essay_word_count=essay_word_count,
            rec_letters_required=rec_letters_required,
            interview_required=interview_required,
            competitiveness=competitiveness,
            application_url=application_url,
            notes=notes,
            renewable=renewable,
            category=category,
            estimated_hours=estimated_hours,
            days_until_deadline=days_until,
            date_researched=self.today.strftime('%Y-%m-%d')
        )

        scholarship.priority_score = self.calculate_priority_score(scholarship)
        self.scholarships.append(scholarship)

    def research_scholarships(self):
        """Generate scholarships dynamically based on student profile"""

        # === LOAD SCHOLARSHIPS FROM DATABASE ===
        self.load_scholarships_from_database()

        # === NATIONAL MERIT-BASED SCHOLARSHIPS (Universal) ===
        self.add_universal_scholarships()

        # === UNIVERSITY-SPECIFIC SCHOLARSHIPS ===
        self.add_university_scholarships()

        # === MAJOR/DISCIPLINE-SPECIFIC SCHOLARSHIPS ===
        self.add_major_scholarships()

        # === HERITAGE/DIVERSITY SCHOLARSHIPS ===
        self.add_diversity_scholarships()

        # === STATE-SPECIFIC SCHOLARSHIPS ===
        self.add_state_scholarships()

        # === FIRST-GENERATION SCHOLARSHIPS ===
        if self.first_gen:
            self.add_first_gen_scholarships()

        # === MILITARY SCHOLARSHIPS ===
        if self.military:
            self.add_military_scholarships()

        # === DISABILITY SCHOLARSHIPS ===
        if self.disability and self.disability.lower() != 'not specified':
            self.add_disability_scholarships()

        # === CORPORATE SCHOLARSHIPS (ONLY FOR STEM MAJORS) ===
        if self.is_stem_major():
            self.add_corporate_scholarships()

        # === CLUBS/ORGANIZATIONS SCHOLARSHIPS ===
        if self.clubs and self.clubs.lower() != 'not specified':
            self.add_club_scholarships()

        # === ATHLETICS SCHOLARSHIPS ===
        if self.athletics and self.athletics.lower() != 'not specified':
            self.add_athletics_scholarships()

        # === SKILLS-BASED SCHOLARSHIPS ===
        if self.skills and self.skills.lower() != 'not specified':
            self.add_skills_scholarships()

        # === ADDITIONAL NATIONAL & COMPETITIVE SCHOLARSHIPS ===
        self.add_national_competitive_scholarships()

        # === ADDITIONAL CORPORATE SCHOLARSHIPS (STEM ONLY) ===
        if self.is_stem_major():
            self.add_additional_corporate_scholarships()

        # === REMOVE DUPLICATE SCHOLARSHIPS ===
        # Database scholarships may overlap with hardcoded ones
        total_before_dedup = len(self.scholarships)
        seen_names = set()
        unique_scholarships = []
        for s in self.scholarships:
            if s.name not in seen_names:
                seen_names.add(s.name)
                unique_scholarships.append(s)

        self.scholarships = unique_scholarships
        duplicates_removed = total_before_dedup - len(self.scholarships)

        if duplicates_removed > 0:
            print(f"✓ Removed {duplicates_removed} duplicate scholarship(s)")

        # === FILTER OUT EXPIRED SCHOLARSHIPS ===
        total_before = len(self.scholarships)
        self.scholarships = [s for s in self.scholarships if not s.is_expired()]
        expired_count = total_before - len(self.scholarships)

        if expired_count > 0:
            print(f"✓ Filtered out {expired_count} expired scholarship(s)")

    def add_universal_scholarships(self):
        """Add universal merit-based scholarships applicable to all students"""

        # These scholarships require US citizenship - skip for international students
        # Coca-Cola is only for high school seniors
        if self.residency.lower() != "international" and "high school senior" in self.year.lower():
            self.add_scholarship(
                "Coca-Cola Scholars Program", 20000, 20000,
                "$20,000", "October 31, 2025", 3.0, 3.5,
                "Leadership, academic excellence, community service, US citizenship required",
                True, 1000, 2, True, "Very High",
                "https://www.coca-colascholarsfoundation.org",
                "One of largest corporate scholarship programs; high school seniors only",
                False, "National", 7.0
            )

        # Dell, Horatio Alger, and Elks are also for high school seniors
        if self.residency.lower() != "international" and "high school senior" in self.year.lower():
            self.add_scholarship(
                "Dell Scholars Program", 20000, 20000,
                "$20,000 + laptop", "December 1, 2025", 2.4, 3.0,
                "Students who overcome significant obstacles, US citizenship required",
                True, 800, 2, True, "High",
                "https://www.dellscholars.org",
                "Focus on persistence and determination; high school seniors only",
                True, "Corporate", 6.0
            )

            self.add_scholarship(
                "Horatio Alger Scholarship", 7500, 25000,
                "$7,500-$25,000", "March 15, 2026", 2.0, 3.0,
                "Overcoming adversity, financial need, US citizenship required",
                True, 800, 2, True, "Medium",
                "https://scholars.horatioalger.org",
                "Focus on resilience and character; high school seniors only",
                False, "National", 5.0
            )

            self.add_scholarship(
                "Elks National Foundation Most Valuable Student", 4000, 12500,
                "$4,000-$12,500/year (4 years)", "November 2025", 3.5, 3.7,
                "Leadership, scholarship, financial need, US citizenship required",
                True, 1000, 2, False, "High",
                "https://www.elks.org/scholars/scholarships/MVS.cfm",
                "Very competitive national scholarship; high school seniors only",
                True, "National", 6.0
            )

    def add_university_scholarships(self):
        """Add scholarships specific to the student's university"""

        uni_name = self.university

        # Generic university scholarships - removed (dynamic URL generation creates invalid domains)

        # Residency-based scholarships - removed (dynamic URL generation creates invalid domains)

        # === PURDUE UNIVERSITY SPECIFIC SCHOLARSHIPS ===
        if 'purdue' in self.university.lower():
            # These are for current college students only (not high school)
            if "high school senior" not in self.year.lower():
                self.add_scholarship(
                    "Purdue Engineering Academic Excellence Scholarship", 2000, 5000,
                    "$2,000-$5,000", "March 1, 2026", 3.5, 3.7,
                    "Sophomore engineering students, demonstrated academic excellence",
                    True, 600, 2, False, "High",
                    "https://engineering.purdue.edu/Engr/Academics/Scholarships",
                    "Purdue College of Engineering merit award",
                    False, "Purdue", 4.0
                )

        # Purdue Trustees Scholarship (Continuing) - removed (broken link/404 error)

            self.add_scholarship(
                "Engineering Education Foundation Scholarships", 1500, 5000,
                "$1,500-$5,000", "March 15, 2026", 3.0, 3.5,
                "Engineering students regardless of residency",
                True, 500, 2, False, "Medium",
                "https://engineering.purdue.edu/Engr/Academics/Scholarships",
                "Various programs available",
                True, "Purdue", 3.0
            )

            # Department-specific scholarships
            if 'mechanical' in self.major.lower() or 'mechanical' in self.discipline.lower():
                self.add_scholarship(
                    "Purdue School of Mechanical Engineering Scholarship", 1000, 3000,
                    "$1,000-$3,000", "February 28, 2026", 3.4, 3.6,
                    "Mechanical engineering majors",
                    True, 500, 1, False, "Medium",
                    "https://engineering.purdue.edu/ME/Academics/Scholarships",
                    "ME department scholarships",
                    True, "Purdue", 3.0
                )

            if 'electrical' in self.major.lower() or 'computer eng' in self.major.lower():
                self.add_scholarship(
                    "Purdue School of Electrical and Computer Engineering Award", 1500, 4000,
                    "$1,500-$4,000", "February 28, 2026", 3.5, 3.7,
                    "ECE majors, demonstrated excellence",
                    True, 600, 2, False, "Medium",
                    "https://engineering.purdue.edu/ECE/Academics/Scholarships",
                    "ECE department awards",
                    True, "Purdue", 3.5
                )

            if 'civil' in self.major.lower():
                self.add_scholarship(
                    "Purdue School of Civil Engineering Scholarship", 1000, 3500,
                    "$1,000-$3,500", "March 10, 2026", 3.3, 3.6,
                    "Civil engineering majors",
                    True, 500, 1, False, "Medium",
                    "https://engineering.purdue.edu/CE/Academics/Scholarships",
                    "Civil Engineering department scholarships",
                    True, "Purdue", 3.0
                )

            # Out-of-state Purdue scholarships
            if "out-of-state" in self.residency.lower() or "out of state" in self.residency.lower():
                self.add_scholarship(
                    "Purdue Out-of-State Engineering Merit Award", 1000, 4000,
                    "$1,000-$4,000", "March 1, 2026", 3.3, 3.5,
                    "Out-of-state engineering students",
                    False, 0, 0, False, "Medium",
                    "https://www.purdue.edu/dfa/currentstudents/continuing.html",
                    "Automatic consideration",
                    True, "Purdue", 1.0
                )

                self.add_scholarship(
                    "Boilermaker Out-of-State Tuition Grant", 2000, 6000,
                    "$2,000-$6,000", "Rolling", 3.0, 3.3,
                    "Out-of-state students, financial need and merit",
                    False, 0, 0, False, "Medium",
                    "https://www.purdue.edu/financialaid/",
                    "Rolling admissions, apply early",
                    True, "Purdue", 2.0
                )

            # National Merit at Purdue
            self.add_scholarship(
                "National Merit Finalist Scholarship at Purdue", 2000, 2000,
                "$2,000/year renewable", "Listed Purdue first choice", 0.0, 3.5,
                "National Merit Finalists",
                False, 0, 0, False, "Very High",
                "https://nationalmerit.org/s/1758/interior.aspx?sid=1758&gid=2&pgid=424",
                "Must list Purdue as first choice",
                True, "Purdue", 5.0
            )

    def add_major_scholarships(self):
        """Add scholarships specific to student's major/discipline"""

        # STEM/Engineering scholarships
        if self.is_stem_major():
            self.add_stem_scholarships()

        # Business scholarships
        if self.is_business_major():
            self.add_business_scholarships()

        # Health/Medical scholarships
        if self.is_health_major():
            self.add_health_scholarships()

        # Arts/Humanities scholarships
        if self.is_arts_humanities_major():
            self.add_arts_scholarships()

    def add_stem_scholarships(self):
        """Add STEM-specific scholarships"""

        # SMART Scholarship requires US citizenship - skip for international students
        if self.residency.lower() != "international":
            self.add_scholarship(
                "SMART Scholarship for Service Program", 50000, 80000,
                "Full tuition + stipend + internship", "December 1, 2025", 3.0, 3.3,
                "STEM students, US citizenship, DoD commitment",
                True, 1500, 3, True, "High",
                "https://www.smartscholarship.org",
                "Service commitment required",
                True, "National", 10.0
            )

        self.add_scholarship(
            "Barry Goldwater Scholarship", 7500, 7500,
            "Up to $7,500", "January 2026", 3.7, 3.8,
            "Sophomore/Junior STEM students",
            True, 1000, 3, True, "Very High",
            "https://goldwaterscholarship.gov",
            "Requires faculty nomination",
            False, "National", 8.0
        )

        self.add_scholarship(
            "Generation Google Scholarship", 10000, 10000,
            "$10,000", "December 8, 2025", 3.3, 3.6,
            "CS/Computer Engineering students",
            True, 800, 2, False, "High",
            "https://buildyourfuture.withgoogle.com/scholarships/generation-google-scholarship",
            "For underrepresented groups in tech",
            False, "Corporate", 5.0
        )

        # === ADDITIONAL MERIT-BASED STEM SCHOLARSHIPS ===

        # NSF S-STEM Program
        if 'stem' in self.discipline.lower() or any(field in self.major.lower() for field in ['science', 'technology', 'engineering', 'math']):
            self.add_scholarship(
                "NSF S-STEM Scholarship Program", 1000, 10000,
                "$1,000-$10,000", "Varies by institution", 3.0, 3.5,
                "STEM students at participating universities",
                True, 500, 2, False, "Medium",
                "https://www.nsf.gov/funding/opportunities/s-stem-nsf-scholarships-science-technology-engineering-mathematics",
                "Check with your university's STEM department",
                False, "Federal/STEM", 4.0
            )

        # IEEE Computer Society Scholarship
        if 'computer' in self.major.lower() or 'ieee' in self.clubs.lower():
            self.add_scholarship(
                "IEEE Computer Society Scholarship", 2000, 4000,
                "$2,000-$4,000", "May 31, 2026", 2.5, 3.0,
                "Computer Science/Engineering students, IEEE members preferred",
                True, 300, 2, False, "Medium",
                "https://www.computer.org/volunteering/awards/scholarships",
                "IEEE membership strongly encouraged",
                False, "Professional Org", 3.5
            )

        # NCWIT Collegiate Award
        if self.gender.lower() in ['female', 'woman', 'non-binary'] and 'computer' in self.major.lower():
            self.add_scholarship(
                "NCWIT Collegiate Award", 5000, 10000,
                "$5,000-$10,000", "November 2025", 3.0, 3.5,
                "Women in computing with demonstrated leadership",
                True, 600, 3, False, "High",
                "https://www.aspirations.org/awards-programs/aic-collegiate-award",
                "Recognizes technical and leadership accomplishments",
                False, "Diversity/Tech", 5.0
            )

        # Palantir Women in Technology Scholarship
        if self.gender.lower() in ['female', 'woman'] and 'computer' in self.major.lower():
            self.add_scholarship(
                "Palantir Women in Technology Scholarship", 7000, 7000,
                "$7,000", "April 1, 2026", 3.0, 3.5,
                "Women studying CS/Engineering with strong academic record",
                True, 500, 2, False, "High",
                "https://www.palantir.com/careers/students/scholarship/wit-north-america/",
                "Includes mentorship and networking opportunities",
                False, "Corporate", 5.5
            )

        # ASME Scholarship
        if 'mechanical' in self.major.lower() or 'asme' in self.clubs.lower():
            self.add_scholarship(
                "American Society of Mechanical Engineers (ASME) Scholarship", 2500, 11000,
                "$2,500-$11,000", "March 15, 2026", 3.0, 3.5,
                "Mechanical Engineering students, ASME membership required",
                True, 600, 2, False, "Medium",
                "https://www.asme.org/asme-programs/students-and-faculty/scholarships",
                "Multiple scholarship programs available",
                False, "Professional Org", 4.5
            )

        # SAE Engineering Scholarships
        if 'engineering' in self.major.lower() or 'automotive' in self.major.lower():
            self.add_scholarship(
                "SAE Engineering Scholarships", 1000, 5000,
                "$1,000-$5,000", "March 15, 2026", 3.0, 3.5,
                "Engineering students interested in mobility/automotive",
                True, 400, 2, False, "Medium",
                "https://www.sae.org/participate/scholarships",
                "Multiple scholarships for various engineering disciplines",
                False, "Professional Org", 3.5
            )

        # American Chemical Society Scholars Program
        if 'chemistry' in self.major.lower() or 'chemical' in self.major.lower():
            self.add_scholarship(
                "American Chemical Society Scholars Program", 1000, 5000,
                "$1,000-$5,000 (renewable)", "March 1, 2026", 3.0, 3.5,
                "Chemistry/Chemical Engineering students from underrepresented groups",
                True, 500, 2, False, "Medium",
                "https://www.acs.org/funding/scholarships/acsscholars.html",
                "Renewable for up to 4 years",
                False, "Professional Org", 4.0
            )

        # Davidson Fellows Scholarship
        student_gpa = float(self.student_profile.get('gpa', 0))
        if student_gpa >= 3.5:
            self.add_scholarship(
                "Davidson Fellows Scholarship", 10000, 50000,
                "$10,000-$50,000", "Second Wednesday in February 2026", 3.5, 4.0,
                "Students with extraordinary accomplishments in STEM, literature, music",
                True, 1200, 4, False, "Very High",
                "https://www.davidsongifted.org/gifted-programs/fellows-scholarship/",
                "Highly prestigious, requires significant original work",
                False, "National Merit", 8.0
            )

        # Hispanic Scholarship Fund
        if 'hispanic' in self.heritage.lower() or 'latino' in self.heritage.lower() or 'latina' in self.heritage.lower():
            self.add_scholarship(
                "Hispanic Scholarship Fund", 500, 5000,
                "$500-$5,000", "February 15, 2026", 3.0, 3.5,
                "Hispanic/Latino students pursuing any major",
                True, 600, 2, False, "Medium",
                "https://www.hsf.net/scholarship",
                "Merit-based, renewable scholarship",
                False, "Diversity", 4.0
            )

        # UNCF Scholarships
        if 'black' in self.heritage.lower() or 'african american' in self.heritage.lower():
            self.add_scholarship(
                "United Negro College Fund (UNCF) Scholarships", 2000, 10000,
                "$2,000-$10,000", "Varies by program", 2.5, 3.5,
                "African American students, multiple scholarship programs",
                True, 700, 2, False, "Medium",
                "https://www.uncf.org/scholarships",
                "Over 400 scholarship programs available",
                False, "Diversity", 4.5
            )

    def add_business_scholarships(self):
        """Add business-specific scholarships"""

        self.add_scholarship(
            "National Business Scholars Association", 2500, 10000,
            "$2,500-$10,000", "February 28, 2026", 3.3, 3.6,
            "Business majors with leadership potential",
            True, 750, 2, False, "Medium",
            "https://www.nbsa.org/scholarships",
            "Various programs for business students",
            False, "Professional Org", 4.0
        )

    def add_health_scholarships(self):
        """Add health/medical-specific scholarships"""

        self.add_scholarship(
            "National Health Service Corps Scholarship", 50000, 120000,
            "$50,000-$120,000 (full tuition + stipend)", "March 31, 2026", 3.0, 3.3,
            "Pre-med, nursing, dental students with service commitment",
            True, 1000, 3, True, "High",
            "https://nhsc.hrsa.gov/scholarships",
            "Service commitment in underserved area required",
            True, "National", 8.0
        )

        self.add_scholarship(
            "American Association of Colleges of Nursing", 2500, 7500,
            "$2,500-$7,500", "March 1, 2026", 3.0, 3.4,
            "Nursing students",
            True, 600, 2, False, "Medium",
            "https://www.aacnnursing.org/Students/Scholarships",
            "Various programs for nursing majors",
            False, "Professional Org", 4.0
        )

        self.add_scholarship(
            "Tylenol Future Care Scholarship", 1000, 10000,
            "$1,000-$10,000", "June 30, 2026", 3.0, 3.3,
            "Students pursuing healthcare degrees",
            True, 500, 2, False, "Medium",
            "https://www.tylenol.com/news/scholarship",
            "For nursing, pre-med, pharmacy, public health students",
            False, "Corporate", 3.5
        )

        self.add_scholarship(
            "AfterCollege-AACN Scholarship Fund", 2500, 2500,
            "$2,500", "June 30, 2026", 3.25, 3.5,
            "Nursing students",
            True, 500, 2, False, "Medium",
            "https://www.aftercollege.com/",
            "For undergraduate and graduate nursing students",
            False, "Professional Org", 3.0
        )

    def add_arts_scholarships(self):
        """Add arts/humanities scholarships"""

        self.add_scholarship(
            "Arts and Humanities Scholarship", 2000, 8000,
            "$2,000-$8,000", "March 15, 2026", 3.0, 3.5,
            "Students pursuing arts, music, or humanities",
            True, 800, 2, False, "Medium",
            "https://www.artsandhumanities.org/scholarships",
            "Portfolio or audition may be required",
            False, "National", 4.5
        )

    def add_diversity_scholarships(self):
        """Add diversity and heritage-based scholarships"""

        heritage_lower = self.heritage.lower()
        # Split into words to avoid substring matches (e.g., 'asian' matching 'caucasian')
        heritage_words = heritage_lower.split()

        # African American scholarships
        if 'african' in heritage_lower or 'black' in heritage_lower:
            self.add_scholarship(
                "United Negro College Fund (UNCF) Scholarship", 5000, 10000,
                "$5,000-$10,000 + internship", "December 2025", 3.0, 3.3,
                "Black/African American students",
                True, 750, 2, True, "High",
                "https://www.uncf.org/scholarships",
                "Includes mentorship and internships",
                False, "Diversity", 6.0
            )

        # Thurgood Marshall College Fund STEM Scholarship - removed (broken link/404 error)

        # Hispanic/Latino scholarships
        if 'hispanic' in heritage_lower or 'latin' in heritage_lower or 'mexican' in heritage_lower:
            self.add_scholarship(
                "Hispanic Scholarship Fund", 500, 5000,
                "$500-$5,000", "February 15, 2026", 2.5, 3.0,
                "Hispanic heritage students",
                True, 600, 1, False, "Medium",
                "https://www.hsf.net/scholarship",
                "One of largest Latinx scholarship programs",
                False, "Diversity", 3.5
            )

        # Asian American scholarships
        # Use word-based matching to avoid matching 'asian' in 'caucasian'
        if any(word in ['asian', 'pacific', 'chinese', 'japanese', 'korean', 'vietnamese', 'filipino', 'indian'] for word in heritage_words):
            self.add_scholarship(
                "Asian & Pacific Islander American Scholarship Fund", 2500, 20000,
                "$2,500-$20,000", "January 15, 2026", 2.7, 3.3,
                "Asian American and Pacific Islander students",
                True, 500, 2, False, "Medium",
                "https://www.apiasf.org/scholarship.html",
                "Multiple scholarship programs",
                False, "Diversity", 4.0
            )

        # Native American scholarships
        if 'native' in heritage_lower or 'indigenous' in heritage_lower or 'american indian' in heritage_lower:
            self.add_scholarship(
                "American Indian Science & Engineering Society (AISES)", 1000, 5000,
                "$1,000-$5,000", "May 31, 2026", 2.5, 3.0,
                "Native American/Alaska Native STEM students",
                True, 500, 2, False, "Low",
                "https://www.aises.org/scholarships",
                "Membership encouraged",
                False, "Diversity", 3.0
            )

        # Latvian/Baltic heritage scholarships
        if 'latvian' in heritage_lower or 'latvia' in heritage_lower or 'baltic' in heritage_lower:
            self.add_scholarship(
                "American Latvian Association Scholarship", 1000, 3000,
                "$1,000-$3,000", "March 15, 2026", 2.5, 3.0,
                "Students of Latvian heritage",
                True, 500, 2, False, "Low",
                "https://www.alausa.org/scholarships",
                "For students with Latvian or Baltic heritage",
                False, "Heritage", 3.0
            )

            self.add_scholarship(
                "Baltic American Freedom Foundation Scholarship", 5000, 15000,
                "$5,000-$15,000", "February 28, 2026", 3.0, 3.5,
                "Students from Baltic states or of Baltic heritage",
                True, 800, 3, True, "Medium",
                "https://www.balticfreedom.org/scholarships",
                "Study abroad and exchange programs available",
                False, "Heritage", 5.0
            )

            self.add_scholarship(
                "Latvian Welfare Association Scholarship", 500, 2000,
                "$500-$2,000", "April 30, 2026", 2.5, 3.0,
                "Students of Latvian descent",
                True, 400, 1, False, "Low",
                "https://www.latvianwelfare.org/",
                "Supporting Latvian heritage students",
                False, "Heritage", 2.5
            )

        # Gender-based scholarships
        if 'female' in self.gender.lower() or 'woman' in self.gender.lower():
            self.add_scholarship(
                "Women in STEM Scholarship", 2500, 10000,
                "$2,500-$10,000", "February 1, 2026", 3.0, 3.4,
                "Women pursuing STEM degrees",
                True, 700, 2, False, "Medium",
                "https://www.swe.org/scholarships/",
                "Encouraging women in STEM fields",
                False, "Diversity", 4.5
            )

        # LGBTQ+ scholarships
        # Point Foundation LGBTQ Scholarship - removed (broken link/404 error)

    def add_state_scholarships(self):
        """Add state-specific scholarships"""

        # State scholar awards - removed (dynamic URL generation creates invalid/broken links)

    def add_first_gen_scholarships(self):
        """Add first-generation college student scholarships"""

        self.add_scholarship(
            "First Generation Scholarship Program", 2500, 10000,
            "$2,500-$10,000", "February 15, 2026", 2.8, 3.3,
            "First-generation college students",
            True, 700, 2, False, "Medium",
            "https://www.firstgen.org/",
            "Support for students whose parents didn't attend college",
            False, "National", 4.5
        )

    def add_military_scholarships(self):
        """Add military-affiliated scholarships"""

        self.add_scholarship(
            "Military Dependents Scholarship", 5000, 15000,
            "$5,000-$15,000", "March 1, 2026", 2.5, 3.0,
            "Dependents of military service members",
            True, 600, 2, False, "Medium",
            "https://www.militaryscholar.org",
            "For children/spouses of active duty or veterans",
            True, "Military", 4.0
        )

    def add_disability_scholarships(self):
        """Add scholarships for students with disabilities"""
        disability_lower = self.disability.lower()

        # Universal disability scholarships (all types)
        # National Federation of the Blind Scholarship - removed (broken link/404 error)

        self.add_scholarship(
            "Google Lime Scholarship", 10000, 10000,
            "$10,000", "December 11, 2025", 3.0, 3.5,
            "Students with disabilities pursuing CS/Engineering",
            True, 600, 2, False, "High",
            "https://www.limeconnect.com/programs/page/google-lime-scholarship",
            "For students with visible or invisible disabilities in tech fields",
            False, "Disability", 5.0
        )

        # Microsoft Disability Scholarship - removed (broken link/404 error)

        # Incight Scholarships - removed (broken link/404 error)

        # Autism spectrum specific - removed scholarships (broken links/404 errors)
        # Organization for Autism Research (OAR) Scholarship - removed (broken link/404 error)
        # Autism Scholarship - ACT Today! - removed (broken link/404 error)

        # ADHD and Learning Disabilities
        if any(x in disability_lower for x in ['adhd', 'learning disability', 'dyslexia']):
            self.add_scholarship(
                "Anne Ford Scholarship", 10000, 10000,
                "$10,000", "April 30, 2026", 3.0, 3.5,
                "High school seniors with documented learning disabilities",
                True, 800, 3, False, "High",
                "https://ncld.org/scholarships/anne-ford-scholarship/",
                "Prestigious award from National Center for Learning Disabilities",
                False, "Disability", 5.5
            )

            self.add_scholarship(
                "Allegra Ford Thomas Scholarship", 5000, 5000,
                "$5,000", "April 30, 2026", 2.5, 3.0,
                "Graduating high school seniors with learning disabilities",
                True, 600, 2, False, "Medium",
                "https://ncld.org/scholarships/allegra-ford-thomas-scholarship/",
                "From NCLD, for students pursuing undergraduate degrees",
                False, "Disability", 4.0
            )

        if 'dyslexia' in disability_lower:
            self.add_scholarship(
                "Marion Huber Learning Through Listening Award", 2000, 6000,
                "$2,000-$6,000", "March 15, 2026", 3.0, 3.5,
                "High school seniors with learning disabilities using audiobooks",
                True, 500, 3, False, "Medium",
                "https://learningally.org/scholarships",
                "For students who benefit from audiobooks due to dyslexia/LD",
                False, "Disability", 4.0
            )

        # Physical disabilities
        if 'physical' in disability_lower:
            self.add_scholarship(
                "Lime Connect Pathways Scholarship", 1000, 10000,
                "$1,000-$10,000", "December 11, 2025", 2.5, 3.0,
                "Students with visible or invisible disabilities",
                True, 400, 1, False, "Medium",
                "https://www.limeconnect.com/opportunities",
                "Multiple corporate partners; broad disability categories",
                False, "Disability", 4.0
            )

            self.add_scholarship(
                "Boomer Esiason Foundation Scholarship", 10000, 10000,
                "$10,000", "May 31, 2026", 2.5, 3.0,
                "Students with cystic fibrosis",
                True, 600, 2, False, "Medium",
                "https://esiason.org/thriving-with-cf/scholarships/",
                "For students living with CF pursuing higher education",
                False, "Disability", 4.5
            )

        # Visual impairments
        if any(x in disability_lower for x in ['visual', 'blind', 'vision']):
            self.add_scholarship(
                "American Council of the Blind Scholarship", 1000, 5000,
                "$1,000-$5,000", "February 15, 2026", 2.5, 3.0,
                "Blind or visually impaired students",
                True, 500, 2, False, "Medium",
                "https://www.acb.org/scholarships",
                "20+ scholarships for blind/low vision students",
                False, "Disability", 4.0
            )

        # Hearing impairments
        if any(x in disability_lower for x in ['hearing', 'deaf', 'hard of hearing']):
            self.add_scholarship(
                "Alexander Graham Bell Scholarship", 1000, 10000,
                "$1,000-$10,000", "March 5, 2026", 3.0, 3.5,
                "Students who are deaf or hard of hearing",
                True, 800, 3, False, "High",
                "https://www.agbell.org/Scholarships",
                "For students with hearing loss using listening and spoken language",
                False, "Disability", 5.0
            )

        # Sertoma Scholarship for Hard of Hearing - removed (broken link/404 error)

        # Chronic illness
        if 'chronic' in disability_lower:
            self.add_scholarship(
                "Vitality Medical Scholarship", 500, 500,
                "$500", "September 30, 2026", 2.0, 2.5,
                "Students with chronic health conditions or disabilities",
                True, 300, 0, False, "Low",
                "https://www.vitalitymedical.com/scholarship.html",
                "Biannual scholarship for students managing chronic conditions",
                False, "Disability", 3.0
            )

    def add_corporate_scholarships(self):
        """Add major corporate scholarships"""

        self.add_scholarship(
            "Amazon Future Engineer Scholarship", 10000, 40000,
            "$40,000 ($10k/year)", "January 30, 2026", 3.0, 3.3,
            "Computer Science students",
            True, 750, 2, False, "High",
            "https://www.amazonfutureengineer.com/scholarships",
            "Includes guaranteed Amazon internship",
            True, "Corporate", 5.0
        )

        # Microsoft Tuition Scholarship - removed (broken link/404 error)

        self.add_scholarship(
            "Apple Scholars Program", 25000, 25000,
            "$25,000", "April 15, 2026", 3.6, 3.8,
            "Engineering/CS students",
            True, 1000, 3, True, "Very High",
            "https://www.apple.com/careers/us/students.html",
            "Includes internship and mentorship",
            False, "Corporate", 7.0
        )

    def add_club_scholarships(self):
        """Add scholarships based on club/organization memberships"""
        clubs_lower = self.clubs.lower()

        # IEEE - Institute of Electrical and Electronics Engineers
        if 'ieee' in clubs_lower:
            self.add_scholarship(
                "IEEE Presidents' Scholarship", 10000, 10000,
                "$10,000", "May 2026", 3.5, 3.7,
                "IEEE student members with innovative projects",
                True, 800, 3, True, "Very High",
                "https://www.ieee.org/membership/students/scholarships/",
                "Highly competitive; demonstrates exceptional innovation",
                False, "Professional Org", 6.0
            )

        # SWE - Society of Women Engineers
        if 'swe' in clubs_lower or 'women engineers' in clubs_lower or 'society of women' in clubs_lower:
            self.add_scholarship(
                "Society of Women Engineers (SWE) Scholarship", 1000, 15000,
                "$1,000-$15,000", "February 15, 2026", 3.0, 3.5,
                "SWE members or engineering students",
                True, 600, 2, False, "Medium",
                "https://swe.org/scholarships/",
                "Multiple scholarships available, open to all genders",
                False, "Professional Org", 4.0
            )

        # NSBE - National Society of Black Engineers
        if 'nsbe' in clubs_lower or 'black engineers' in clubs_lower:
            self.add_scholarship(
                "National Society of Black Engineers (NSBE) Scholarship", 1000, 10000,
                "$1,000-$10,000", "January 31, 2026", 3.0, 3.3,
                "NSBE members, Black/African American engineering students",
                True, 500, 2, False, "Medium",
                "https://nsbe.org/scholarships",
                "Multiple programs available for NSBE members",
                False, "Diversity", 4.0
            )

        # SHPE - Society of Hispanic Professional Engineers
        if 'shpe' in clubs_lower or 'hispanic' in clubs_lower:
            self.add_scholarship(
                "Society of Hispanic Professional Engineers (SHPE)", 1000, 5000,
                "$1,000-$5,000", "April 30, 2026", 3.0, 3.3,
                "SHPE members or Hispanic/Latinx students",
                True, 500, 2, False, "Medium",
                "https://shpe.org/students/scholarships/",
                "Engineering and STEM focus",
                False, "Diversity", 3.5
            )

        # ASME - American Society of Mechanical Engineers
        if 'asme' in clubs_lower or 'mechanical' in clubs_lower:
            self.add_scholarship(
                "American Society of Mechanical Engineers (ASME) Scholarship", 1500, 13000,
                "$1,500-$13,000", "March 1, 2026", 3.0, 3.4,
                "ASME student members",
                True, 500, 2, False, "Medium",
                "https://www.asme.org/asme-programs/students-and-faculty/scholarships",
                "Multiple scholarship programs for ASME members",
                False, "Professional Org", 3.5
            )

        # ASCE - American Society of Civil Engineers
        if 'asce' in clubs_lower or 'civil' in clubs_lower:
            self.add_scholarship(
                "American Society of Civil Engineers (ASCE) Scholarship", 2000, 5000,
                "$2,000-$5,000", "February 10, 2026", 3.0, 3.4,
                "ASCE student members",
                True, 500, 2, False, "Medium",
                "https://www.asce.org/career-growth/student-opportunities/scholarships",
                "Multiple scholarships for civil engineering students",
                False, "Professional Org", 3.5
            )

        # SAE - Society of Automotive Engineers
        if 'sae' in clubs_lower or 'automotive' in clubs_lower:
            self.add_scholarship(
                "Society of Automotive Engineers (SAE) Scholarship", 1000, 6000,
                "$1,000-$6,000", "January 15, 2026", 3.0, 3.4,
                "SAE student members interested in automotive/mobility",
                True, 500, 2, False, "Medium",
                "https://www.sae.org/participate/scholarships",
                "Focus on automotive, aerospace, commercial vehicle engineering",
                False, "Professional Org", 3.5
            )

        # Tau Beta Pi - Engineering Honor Society
        if 'tau beta pi' in clubs_lower or 'tbp' in clubs_lower or 'honor society' in clubs_lower:
            self.add_scholarship(
                "Tau Beta Pi Engineering Honor Society Scholarships", 2000, 10000,
                "$2,000-$10,000", "April 2026", 3.7, 3.8,
                "Tau Beta Pi members",
                True, 600, 3, False, "High",
                "https://www.tbp.org/scholarships.cfm",
                "Must be Tau Beta Pi member; high GPA required",
                False, "Professional Org", 4.0
            )

        # ACM - Association for Computing Machinery - removed scholarship (broken link/404 error)
        # ACM Student Scholarship - removed (broken link/404 error)

        # Robotics Club
        if 'robot' in clubs_lower:
            self.add_scholarship(
                "Robotics Education & Competition Foundation Scholarship", 1000, 5000,
                "$1,000-$5,000", "February 28, 2026", 3.0, 3.3,
                "Students involved in robotics competitions",
                True, 500, 2, False, "Medium",
                "https://www.roboticseducation.org/",
                "For participants in FIRST, VEX, or other robotics programs",
                False, "Professional Org", 3.0
            )

        # === HIGH SCHOOL CLUBS ===

        # National Honor Society
        if 'national honor society' in clubs_lower or 'nhs' in clubs_lower:
            self.add_scholarship(
                "National Honor Society Scholarship", 2500, 10000,
                "$2,500-$10,000", "February 15, 2026", 3.5, 3.7,
                "Active NHS members with leadership and service",
                True, 700, 3, False, "High",
                "https://www.nhs.us/students/scholarships/",
                "NHS membership and leadership activities required",
                False, "High School Activity", 4.0
            )

        # Science Club/Science Olympiad - removed generic scholarship

        # Math Team/Math Club - removed generic scholarship

        # Debate Team/Forensics/Speech - removed generic scholarship

        # Student Government/Class Officer - removed generic scholarship

        # Language Clubs (French, Spanish, etc.) - removed generic scholarship

        # Drama/Theater Club - removed generic scholarship

        # Key Club
        if 'key club' in clubs_lower or 'kiwanis' in clubs_lower:
            self.add_scholarship(
                "Key Club Service Leadership Scholarship", 1500, 5000,
                "$1,500-$5,000", "March 15, 2026", 3.0, 3.3,
                "Active Key Club members with community service",
                True, 600, 2, False, "Medium",
                "https://www.keyclub.org/",
                "Document service hours and Key Club leadership",
                False, "High School Activity", 3.0
            )

        # DECA/FBLA (Business Clubs) - removed generic scholarship

        # Yearbook/Newspaper/Journalism - removed generic scholarship

        # Environmental/Green Club - removed generic scholarship

    def add_athletics_scholarships(self):
        """Add scholarships based on athletics participation"""
        athletics_lower = self.athletics.lower()

        # NCAA Athletes
        # any(sport in athletics_lower for sport in ['ncaa', 'varsity', 'division']) - removed scholarship (broken link/404 error)
        # NCAA Division I/II/III Athletic Scholarship - removed (broken link/404 error)

        # Scholar-Athlete Awards - removed scholarship (broken link/404 error)
        # Scholar-Athlete Scholarship - removed (broken link/404 error)

        # Specific sport scholarships - removed generic scholarship

        # Intramural/Club Sports - removed scholarship (dynamic URL generation creates invalid links)

    def add_skills_scholarships(self):
        """Add scholarships based on specific skills"""
        skills_lower = self.skills.lower()

        # Programming/Coding Skills - removed generic scholarship

        # Research Skills - removed scholarship (dynamic URL generation creates invalid links)

        # Leadership Skills - removed scholarship (dynamic URL generation creates invalid links)

        # Community Service/Volunteering - removed generic scholarship

        # Entrepreneurship
        if 'entrepreneur' in skills_lower or 'startup' in skills_lower or 'business owner' in skills_lower:
            self.add_scholarship(
                "Student Entrepreneur Scholarship", 2500, 10000,
                "$2,500-$10,000", "April 15, 2026", 3.0, 3.4,
                "Students who have started or are running a business",
                True, 800, 2, True, "High",
                "https://www.entrepreneurship.org/",
                "Submit business plan or proof of business operation",
                False, "Skills-Based", 5.0
            )

        # CAD/Design Skills - removed generic scholarship

        # Music/Performing Arts Skills - removed generic scholarship

        # Language Skills (Foreign Languages) - removed generic scholarship

        # Visual Arts Skills - removed generic scholarship

        # Writing/Journalism Skills - removed generic scholarship

    def add_national_competitive_scholarships(self):
        """Add high-value national competitive scholarships"""

        # Astronaut Scholarship - High GPA requirement
        if self.user_gpa >= 3.7:
            self.add_scholarship(
                "Astronaut Scholarship Foundation", 15000, 15000,
                "$15,000", "Varies (Feb-Mar 2026)", 3.7, 3.8,
                "Sophomore+ STEM students",
                True, 800, 2, True, "Very High",
                "https://astronautscholarship.org",
                "Must be nominated by university",
                False, "National", 7.0
            )

        # Jack Kent Cooke - Transfer students or high GPA
        if 'transfer' in self.year.lower() or self.user_gpa >= 3.5:
            self.add_scholarship(
                "Jack Kent Cooke Foundation Undergraduate Transfer Scholarship", 30000, 55000,
                "Up to $55,000/year", "January 2026", 3.5, 3.8,
                "Transfer students with financial need",
                True, 1200, 3, True, "Very High",
                "https://www.jkcf.org/our-scholarships/undergraduate-transfer-scholarship/",
                "One of largest transfer scholarships",
                True, "National", 9.0
            )

        # Paul and Daisy Soros - Immigrants/children of immigrants
        self.add_scholarship(
            "Paul and Daisy Soros Fellowships for New Americans", 25000, 25000,
            "$25,000/year (up to $90k total)", "November 1, 2025", 3.5, 3.7,
            "Immigrants or children of immigrants",
            True, 1000, 3, True, "Very High",
            "https://www.pdsoros.org",
            "For graduate study support",
            True, "National", 8.0
        )

        # GE-Reagan Foundation
        self.add_scholarship(
            "GE-Reagan Foundation Scholarship", 10000, 40000,
            "$10,000-$40,000", "January 5, 2026", 3.3, 3.6,
            "Leadership, drive, integrity, citizenship",
            True, 1000, 3, True, "Very High",
            "https://www.reaganfoundation.org/education/scholarship-programs/",
            "Highly competitive national award",
            False, "Corporate", 7.0
        )

        # Tau Beta Pi - High GPA engineering students
        if self.user_gpa >= 3.7 and self.is_stem_major():
            self.add_scholarship(
                "Tau Beta Pi Engineering Honor Society Scholarships", 2000, 10000,
                "$2,000-$10,000", "April 2026", 3.7, 3.8,
                "Engineering students in top 1/8 (junior)",
                True, 800, 3, False, "High",
                "https://www.tbp.org/scholarships.cfm",
                "Must be TBP member or eligible",
                True, "Professional Org", 5.0
            )

        # === PROFESSIONAL ORGANIZATION SCHOLARSHIPS FOR STEM ===
        if self.is_stem_major():
            # AFCEA - US citizens only
            if self.residency.lower() != "international":
                self.add_scholarship(
                    "AFCEA STEM Major Scholarships", 2500, 5000,
                    "$2,500-$5,000", "Multiple deadlines", 3.0, 3.3,
                    "STEM majors, US citizenship required",
                    True, 500, 1, False, "Medium",
                    "https://www.afcea.org/scholarships",
                    "Military/cybersecurity focus, multiple award categories",
                    True, "Professional Org", 3.5
                )

            # NACME - Underrepresented minorities in engineering
        # NACME Scholarship - removed (broken link/404 error)

            # ASM Materials Education Foundation
            self.add_scholarship(
                "ASM Materials Education Foundation Scholarship", 1000, 10000,
                "$1,000-$10,000", "May 1, 2026", 3.0, 3.3,
                "Materials science/engineering students",
                True, 600, 2, False, "Medium",
                "https://www.asmfoundation.org/programs/scholarships/",
                "For students studying materials science and engineering",
                False, "Professional Org", 4.0
            )

            # AIChE - Chemical engineering students
        # AIChE Scholarships - removed (broken link/404 error)

            # SME Education Foundation
            self.add_scholarship(
                "SME Education Foundation Scholarship", 1000, 5000,
                "$1,000-$5,000", "February 1, 2026", 3.0, 3.3,
                "Manufacturing engineering students",
                True, 500, 2, False, "Medium",
                "https://www.smeef.org/scholarships/",
                "Society for Manufacturing Engineers, multiple scholarship programs",
                False, "Professional Org", 3.5
            )

    def add_additional_corporate_scholarships(self):
        """Add additional major corporate STEM scholarships"""

        # Boeing
        # Boeing Company Scholarship - removed (broken link/404 error)

        # Intel
        self.add_scholarship(
            "Intel Scholarship Program", 5000, 10000,
            "$5,000-$10,000", "January 31, 2026", 3.5, 3.7,
            "Engineering/CS students, underrepresented groups preferred",
            True, 700, 2, False, "High",
            "https://www.intel.com/content/www/us/en/diversity/scholarships.html",
            "Focus on diversity in STEM",
            False, "Corporate", 5.0
        )

        # Tesla
        self.add_scholarship(
            "Tesla Engineering Scholarship", 5000, 10000,
            "$5,000-$10,000", "February 28, 2026", 3.4, 3.6,
            "Engineering students interested in sustainable energy",
            True, 600, 1, False, "High",
            "https://www.tesla.com/careers",
            "Passion for sustainability required",
            False, "Corporate", 4.5
        )

        # Raytheon
        self.add_scholarship(
            "Raytheon Technologies Engineering Scholarship", 5000, 10000,
            "$5,000-$10,000", "March 15, 2026", 3.2, 3.5,
            "Engineering majors, Aerospace/Mechanical/Electrical",
            True, 700, 2, False, "High",
            "https://www.rtx.com/our-company/corporate-responsibility/scholarship-programs",
            "Defense/aerospace focus",
            False, "Corporate", 4.5
        )

        # Northrop Grumman
        # Northrop Grumman Engineering Scholarship - removed (broken link/404 error)

        # Lockheed Martin - US citizens only
        if self.residency.lower() != "international":
            self.add_scholarship(
                "Lockheed Martin STEM Scholarship", 10000, 10000,
                "$10,000", "April 1, 2026", 3.3, 3.6,
                "Engineering/CS majors, US citizenship required",
                True, 800, 2, False, "High",
                "https://www.lockheedmartin.com/en-us/who-we-are/communities/stem-education.html",
                "Focus on aerospace and defense-related fields",
                False, "Corporate", 5.0
            )

    def filter_by_gpa(self, min_gpa: Optional[float] = None) -> List[Scholarship]:
        """Filter scholarships by minimum GPA eligibility"""
        gpa = min_gpa if min_gpa is not None else self.user_gpa
        return [s for s in self.scholarships if s.min_gpa <= gpa]

    def sort_by_priority(self) -> List[Scholarship]:
        """Sort scholarships by priority score (highest first)"""
        return sorted(self.scholarships, key=lambda x: x.priority_score, reverse=True)

    def sort_by_deadline(self) -> List[Scholarship]:
        """Sort scholarships by deadline (soonest first)"""
        return sorted(self.scholarships, key=lambda x: x.days_until_deadline)

    def sort_by_amount(self) -> List[Scholarship]:
        """Sort scholarships by maximum award amount (highest first)"""
        return sorted(self.scholarships, key=lambda x: x.amount_max, reverse=True)

    def get_total_potential_award(self) -> int:
        """Calculate total potential award"""
        eligible = self.filter_by_gpa()
        return sum((s.amount_min + s.amount_max) / 2 for s in eligible)

    def get_urgent_deadlines(self, days: int = 30) -> List[Scholarship]:
        """Get scholarships with deadlines within specified days"""
        return [s for s in self.scholarships
                if s.days_until_deadline <= days and s.days_until_deadline > 0]

    def export_to_csv(self, filename: str = 'scholarships_dynamic.csv',
                      sort_by: str = 'priority') -> str:
        """Export scholarship data to CSV"""
        if not self.scholarships:
            self.research_scholarships()

        # Sort data
        if sort_by == 'priority':
            data = self.sort_by_priority()
        elif sort_by == 'deadline':
            data = self.sort_by_deadline()
        elif sort_by == 'amount':
            data = self.sort_by_amount()
        else:
            data = self.scholarships

        fieldnames = [
            'Priority Score', 'Scholarship Name', 'Award Amount', 'Amount Min', 'Amount Max',
            'Deadline', 'Days Until', 'Min GPA', 'Recommended GPA',
            'Eligibility', 'Essay Required', 'Essay Word Count', 'Rec Letters',
            'Interview', 'Competitiveness', 'Category', 'Renewable',
            'Est. Application Hours', 'Application URL', 'Notes', 'Date Researched'
        ]

        filepath = filename

        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for s in data:
                writer.writerow({
                    'Priority Score': s.priority_score,
                    'Scholarship Name': s.name,
                    'Award Amount': s.amount_display,
                    'Amount Min': s.amount_min,
                    'Amount Max': s.amount_max,
                    'Deadline': s.deadline,
                    'Days Until': s.days_until_deadline if s.days_until_deadline < 999 else 'TBD',
                    'Min GPA': s.min_gpa if s.min_gpa > 0 else 'None',
                    'Recommended GPA': s.recommended_gpa if s.recommended_gpa > 0 else 'N/A',
                    'Eligibility': s.eligibility,
                    'Essay Required': 'Yes' if s.essay_required else 'No',
                    'Essay Word Count': s.essay_word_count if s.essay_word_count > 0 else 'N/A',
                    'Rec Letters': s.rec_letters_required,
                    'Interview': 'Yes' if s.interview_required else 'No',
                    'Competitiveness': s.competitiveness,
                    'Category': s.category,
                    'Renewable': 'Yes' if s.renewable else 'No',
                    'Est. Application Hours': s.estimated_hours,
                    'Application URL': s.application_url,
                    'Notes': s.notes,
                    'Date Researched': s.date_researched
                })

        return filepath

    def generate_summary_stats(self):
        """Generate summary statistics"""
        eligible = self.filter_by_gpa()
        urgent = self.get_urgent_deadlines(30)
        total_potential = self.get_total_potential_award()

        stats = {
            'total_scholarships': len(self.scholarships),
            'gpa_eligible': len(eligible),
            'urgent_deadlines_30_days': len(urgent),
            'total_potential_award': f"${total_potential:,.0f}",
            'by_category': {},
            'by_competitiveness': {},
            'avg_priority_score': sum(s.priority_score for s in eligible) / len(eligible) if eligible else 0
        }

        for s in self.scholarships:
            stats['by_category'][s.category] = stats['by_category'].get(s.category, 0) + 1
            stats['by_competitiveness'][s.competitiveness] = stats['by_competitiveness'].get(s.competitiveness, 0) + 1

        return stats

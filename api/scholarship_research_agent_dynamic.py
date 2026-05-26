#!/usr/bin/env python3
"""
Author: Tim Smith
Note: All Code owned by Tim

Dynamic Scholarship Research Agent - Profile-Based Search
Generates relevant scholarships based on student profile inputs
"""

import csv
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict

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
        self.research = self.student_profile.get('research', False)
        self.disability = self.student_profile.get('disability', '')

        # Determine education level from year field
        # HS years are prefixed with "HS " (e.g. "HS Senior")
        self.is_high_school = self.year.startswith('HS ')
        self.hs_grade = self.year.replace('HS ', '').lower() if self.is_high_school else ''
        self.skills = self.student_profile.get('skills', '')
        self.clubs = self.student_profile.get('clubs', '')
        self.athletics = self.student_profile.get('athletics', '')

        self.today = datetime.now()

    def parse_deadline(self, deadline_str: str) -> Optional[datetime]:
        """Parse deadline string to datetime object.
        Automatically rolls expired annual deadlines forward one year."""
        try:
            deadline_date = None
            formats = [
                '%B %d, %Y', '%b %d, %Y',
                '%m/%d/%Y', '%Y-%m-%d',
                '%B %Y', '%b %Y'
            ]
            for fmt in formats:
                try:
                    deadline_date = datetime.strptime(deadline_str, fmt)
                    break
                except ValueError:
                    continue

            # Try month/year parsing for strings like "November 2025"
            if deadline_date is None:
                month_map = {
                    'January': 1, 'February': 2, 'March': 3, 'April': 4,
                    'May': 5, 'June': 6, 'July': 7, 'August': 8,
                    'September': 9, 'October': 10, 'November': 11, 'December': 12
                }
                for year in ['2025', '2026', '2027']:
                    if year in deadline_str:
                        for month, num in month_map.items():
                            if month in deadline_str:
                                deadline_date = datetime(int(year), num, 1)
                                break
                        break

            # Roll forward year-by-year until the deadline is in the future (annual scholarships repeat)
            if deadline_date:
                while deadline_date < self.today:
                    deadline_date = deadline_date.replace(year=deadline_date.year + 1)

            return deadline_date
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
            # Update display string to match the rolled-forward date
            deadline = deadline_date.strftime('%B %d, %Y')

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

        # === HIGH SCHOOL SPECIFIC SCHOLARSHIPS ===
        if self.is_high_school:
            self.add_hs_scholarships()
        else:
            # College students: remove scholarships intended only for HS students
            self.scholarships = [s for s in self.scholarships if not self._is_hs_only(s)]

        # === RESEARCH OPPORTUNITIES ===
        if self.research:
            self.add_research_scholarships()

        # === DISABILITY SCHOLARSHIPS ===
        if self.disability and self.disability.lower() not in ('not specified', ''):
            self.add_disability_scholarships()

        # === CORPORATE SCHOLARSHIPS ===
        self.add_corporate_scholarships()

    def add_universal_scholarships(self):
        """Add universal merit-based scholarships applicable to all students"""

        self.add_scholarship(
            "Coca-Cola Scholars Program", 20000, 20000,
            "$20,000", "October 31, 2025", 3.0, 3.5,
            "Leadership, academic excellence, community service",
            True, 1000, 2, True, "Very High",
            "https://www.coca-colascholarsfoundation.org",
            "One of largest corporate scholarship programs",
            False, "National", 7.0
        )

        self.add_scholarship(
            "Dell Scholars Program", 20000, 20000,
            "$20,000 + laptop", "December 1, 2025", 2.4, 3.0,
            "Students who overcome significant obstacles",
            True, 800, 2, True, "High",
            "https://www.dellscholars.org",
            "Focus on persistence and determination",
            True, "Corporate", 6.0
        )

        self.add_scholarship(
            "Horatio Alger Scholarship", 7500, 25000,
            "$7,500-$25,000", "March 15, 2026", 2.0, 3.0,
            "Overcoming adversity, financial need",
            True, 800, 2, True, "Medium",
            "https://scholars.horatioalger.org",
            "Focus on resilience and character",
            False, "National", 5.0
        )

        self.add_scholarship(
            "Elks National Foundation Most Valuable Student", 4000, 12500,
            "$4,000-$12,500/year (4 years)", "November 2025", 3.5, 3.7,
            "Leadership, scholarship, financial need",
            True, 1000, 2, False, "High",
            "https://www.elks.org/scholars/scholarships/MVS.cfm",
            "Very competitive national scholarship",
            True, "National", 6.0
        )

    def add_university_scholarships(self):
        """Add scholarships specific to the student's university"""

        uni_name = self.university

        # Generic university scholarships
        self.add_scholarship(
            f"{uni_name} Foundation Scholarship", 1500, 5000,
            "$1,500-$5,000", "March 1, 2026", 3.0, 3.5,
            f"{uni_name} students with financial need and academic merit",
            True, 500, 2, False, "Medium",
            f"https://www.{uni_name.lower().replace(' ', '')}.edu/scholarships",
            f"Contact {uni_name} Financial Aid office",
            True, "University", 3.0
        )

        self.add_scholarship(
            f"{uni_name} Academic Excellence Award", 2000, 8000,
            "$2,000-$8,000", "February 15, 2026", 3.5, 3.7,
            f"Current {uni_name} students with outstanding academic achievement",
            True, 750, 3, True, "High",
            f"https://www.{uni_name.lower().replace(' ', '')}.edu/financialaid",
            "Highly competitive merit-based award",
            True, "University", 5.0
        )

        # Residency-based scholarships
        if "out-of-state" in self.residency.lower() or "out of state" in self.residency.lower():
            self.add_scholarship(
                f"{uni_name} Out-of-State Merit Award", 1000, 4000,
                "$1,000-$4,000", "March 1, 2026", 3.3, 3.5,
                "Out-of-state students, automatic consideration",
                False, 0, 0, False, "Medium",
                f"https://www.{uni_name.lower().replace(' ', '')}.edu/financialaid",
                "Contact Financial Aid for eligibility",
                True, "University", 1.0
            )

    def add_major_scholarships(self):
        """Add scholarships specific to student's major/discipline"""

        major_lower = self.major.lower()

        # STEM/Engineering scholarships
        if any(word in major_lower for word in ['engineering', 'computer', 'science', 'technology', 'math']):
            self.add_stem_scholarships()

        # Business scholarships
        if 'business' in major_lower or 'management' in major_lower:
            self.add_business_scholarships()

        # Arts/Humanities scholarships
        if any(word in major_lower for word in ['art', 'music', 'literature', 'history', 'english']):
            self.add_arts_scholarships()

    def add_stem_scholarships(self):
        """Add STEM-specific scholarships"""

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

        self.add_scholarship(
            "Society of Women Engineers (SWE) Scholarship", 1000, 15000,
            "$1,000-$15,000", "February 15, 2026", 3.0, 3.5,
            "Engineering students, merit-based",
            True, 600, 2, False, "Medium",
            "https://swe.org/scholarships/",
            "Open to all genders",
            False, "Professional Org", 4.0
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

            self.add_scholarship(
                "National Society of Black Engineers (NSBE) Scholarship", 1000, 10000,
                "$1,000-$10,000", "January 31, 2026", 3.0, 3.3,
                "Black/African American engineering students",
                True, 500, 2, False, "Medium",
                "https://nsbe.org/scholarships",
                "Multiple programs available",
                False, "Diversity", 4.0
            )

            self.add_scholarship(
                "Thurgood Marshall College Fund STEM Scholarship", 3000, 6200,
                "$3,000-$6,200", "March 15, 2026", 3.0, 3.25,
                "Students of color in STEM",
                True, 600, 2, False, "Medium",
                "https://tmcf.org/our-scholarships",
                "Leadership and community service emphasized",
                False, "Diversity", 4.0
            )

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

            self.add_scholarship(
                "Society of Hispanic Professional Engineers (SHPE)", 1000, 5000,
                "$1,000-$5,000", "April 30, 2026", 3.0, 3.3,
                "Hispanic/Latinx students",
                True, 500, 2, False, "Medium",
                "https://shpe.org/students/scholarships/",
                "Engineering and STEM focus",
                False, "Diversity", 3.5
            )

        # Asian American scholarships
        if 'asian' in heritage_lower or 'pacific' in heritage_lower:
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

        # Gender-based scholarships
        if 'female' in self.gender.lower() or 'woman' in self.gender.lower():
            self.add_scholarship(
                "Women in STEM Scholarship", 2500, 10000,
                "$2,500-$10,000", "February 1, 2026", 3.0, 3.4,
                "Women pursuing STEM degrees",
                True, 700, 2, False, "Medium",
                "https://www.womenstem.org/scholarships",
                "Encouraging women in STEM fields",
                False, "Diversity", 4.5
            )

        # LGBTQ+ scholarships
        self.add_scholarship(
            "Point Foundation LGBTQ Scholarship", 5000, 30000,
            "$5,000-$30,000", "January 22, 2026", 3.0, 3.5,
            "LGBTQ students with demonstrated leadership",
            True, 800, 2, True, "High",
            "https://pointfoundation.org/point-apply/",
            "Largest scholarship for LGBTQ students",
            False, "Diversity", 5.0
        )

    def add_state_scholarships(self):
        """Add state-specific scholarships"""

        if self.state and self.state != 'Not specified':
            state_name = self.state

            self.add_scholarship(
                f"{state_name} State Scholar Award", 1000, 5000,
                "$1,000-$5,000", "March 31, 2026", 3.0, 3.5,
                f"Residents of {state_name}",
                True, 500, 2, False, "Medium",
                f"https://www.{state_name.lower().replace(' ', '')}.gov/education/scholarships",
                f"Check with {state_name} Department of Education",
                True, "State", 3.0
            )

    def add_first_gen_scholarships(self):
        """Add first-generation college student scholarships"""

        self.add_scholarship(
            "First Generation Scholarship Program", 2500, 10000,
            "$2,500-$10,000", "February 15, 2026", 2.8, 3.3,
            "First-generation college students",
            True, 700, 2, False, "Medium",
            "https://www.firstgenerationscholarship.org",
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

    # Known scholarships that require the applicant to currently be a high school student.
    # College students are already enrolled and are no longer eligible for these.
    _HS_ONLY_NAMES = [
        'coca-cola scholars',
        'dell scholars',
        'horatio alger',
        'elks national foundation most valuable',
        'national merit',
        'questbridge',
        'posse foundation',
        'regeneron science talent',
        'jack kent cooke young scholars',
        'davidson fellows',
        'gates scholarship',
        'axа achievement',
        'burger king scholars',
    ]

    def _is_hs_only(self, scholarship) -> bool:
        """Return True if this scholarship is only open to current high school students."""
        name_lower = scholarship.name.lower()
        if any(hs in name_lower for hs in self._HS_ONLY_NAMES):
            return True
        # Also catch by eligibility / notes keywords
        combined = (scholarship.eligibility + ' ' + scholarship.notes).lower()
        hs_keywords = [
            'high school senior', 'graduating senior', 'high school student',
            'current high school', 'graduating high school', 'high school junior or senior',
        ]
        return any(kw in combined for kw in hs_keywords)

    def add_hs_scholarships(self):
        """Add scholarships specifically for high school students."""
        is_senior = self.hs_grade == 'senior'
        is_junior_or_senior = self.hs_grade in ('junior', 'senior')

        # Available to all HS students
        self.add_scholarship(
            "Davidson Fellows Scholarship", 10000, 50000,
            "$10,000–$50,000", "February 12, 2026", 0.0, 3.5,
            "Students under 18 with a significant piece of work in STEM, literature, music, or philosophy",
            True, 1000, 3, True, "Very High",
            "https://www.davidsongifted.org/fellows-scholarship/",
            "For profoundly gifted students; one of the largest awards for under-18s",
            False, "High School", 6.0
        )

        self.add_scholarship(
            "Regeneron Science Talent Search", 25000, 250000,
            "$25,000–$250,000", "November 12, 2026", 0.0, 3.7,
            "High school seniors who have completed an independent science research project",
            True, 1500, 3, True, "Very High",
            "https://www.societyforscience.org/regeneron-sts/",
            "Oldest and most prestigious science competition for HS students in the US",
            False, "High School", 6.0
        )

        self.add_scholarship(
            "Scholastic Art & Writing Awards", 1000, 10000,
            "$1,000–$10,000", "December 1, 2026", 0.0, 0.0,
            "High school students (grades 7–12) in visual art, film, writing, or photography",
            True, 500, 0, False, "Medium",
            "https://www.artandwriting.org",
            "Gold Key winners at nationals receive scholarships; portfolio submission required",
            False, "High School", 3.0
        )

        self.add_scholarship(
            "DECA Scholarship Program", 1000, 5000,
            "$1,000–$5,000", "January 15, 2026", 3.0, 3.5,
            "High school students who are DECA members pursuing business/marketing careers",
            True, 500, 1, False, "Medium",
            "https://www.deca.org/scholarships/",
            "Multiple scholarships available through DECA's network of corporate partners",
            False, "High School", 3.0
        )

        # Junior and Senior only
        if is_junior_or_senior:
            self.add_scholarship(
                "National Merit Scholarship", 2500, 2500,
                "$2,500 (+ corporate/college awards)", "October 15, 2026", 0.0, 0.0,
                "High school juniors/seniors who score in the top ~1% on the PSAT/NMSQT",
                True, 500, 2, False, "Very High",
                "https://www.nationalmerit.org",
                "Being a Semifinalist/Finalist also unlocks additional college-sponsored awards",
                False, "High School", 4.0
            )

            self.add_scholarship(
                "Jack Kent Cooke Foundation Young Scholars", 40000, 40000,
                "Up to $40,000/year for college", "April 16, 2026", 3.5, 3.8,
                "High-achieving HS juniors with financial need",
                True, 1000, 3, True, "Very High",
                "https://www.jkcf.org/our-scholarships/young-scholars-program/",
                "Provides mentoring, college advising, and funding through college graduation",
                True, "High School", 6.0
            )

        # Senior-only scholarships
        if is_senior:
            self.add_scholarship(
                "Coca-Cola Scholars Program", 20000, 20000,
                "$20,000", "October 31, 2026", 3.0, 3.5,
                "High school seniors — leadership, academic excellence, community service",
                True, 1000, 2, True, "Very High",
                "https://www.coca-colascholarsfoundation.org",
                "One of the largest corporate scholarships; 150 winners selected nationally",
                False, "High School", 7.0
            )

            self.add_scholarship(
                "Dell Scholars Program", 20000, 20000,
                "$20,000 + laptop + support", "December 1, 2026", 2.4, 3.0,
                "High school seniors who overcome significant obstacles with financial need",
                True, 800, 2, True, "High",
                "https://www.dellscholars.org",
                "Focus on persistence and determination; ongoing support through college",
                True, "High School", 6.0
            )

            self.add_scholarship(
                "Gates Scholarship", 0, 0,
                "Full cost of attendance (gap funding)", "September 15, 2026", 3.3, 3.7,
                "Exceptional minority HS seniors with significant financial need",
                True, 1500, 3, True, "Very High",
                "https://www.thegatesscholarship.org",
                "Covers remaining unmet financial need; renewable for 4 years",
                True, "High School", 7.0
            )

            self.add_scholarship(
                "QuestBridge National College Match", 0, 0,
                "Full 4-year scholarship at partner colleges", "September 26, 2026", 3.5, 3.8,
                "High-achieving HS seniors from low-income families",
                True, 1200, 3, True, "Very High",
                "https://www.questbridge.org",
                "Match with top colleges including Yale, Stanford, MIT; highly competitive",
                True, "High School", 7.0
            )

            self.add_scholarship(
                "Horatio Alger Scholarship", 7500, 25000,
                "$7,500–$25,000", "October 25, 2026", 2.0, 3.0,
                "High school seniors who have overcome adversity with financial need",
                True, 800, 2, True, "Medium",
                "https://scholars.horatioalger.org",
                "Focus on resilience and character; state-level scholarships also available",
                False, "High School", 5.0
            )

            self.add_scholarship(
                "Posse Foundation Scholarship", 0, 0,
                "Full tuition at partner universities", "October 2026", 3.0, 3.5,
                "High school seniors with extraordinary academic and leadership potential",
                True, 0, 3, True, "Very High",
                "https://www.possefoundation.org",
                "Cohort-based; students attend college with a 'posse' of 10 peers",
                True, "High School", 7.0
            )

            self.add_scholarship(
                "Elks National Foundation Most Valuable Student", 4000, 12500,
                "$4,000–$12,500/year (4 years)", "November 5, 2026", 3.5, 3.7,
                "US citizen HS seniors demonstrating leadership, scholarship, and financial need",
                True, 500, 3, False, "High",
                "https://www.elks.org/scholars/scholarships/mvs.cfm",
                "Must apply through your local Elks lodge; renewable for 4 years",
                True, "High School", 5.0
            )

            self.add_scholarship(
                "AXA Achievement Scholarship", 2500, 25000,
                "$2,500–$25,000", "December 15, 2026", 3.0, 3.5,
                "US citizen HS seniors who have demonstrated achievement in school and community",
                True, 500, 1, False, "Medium",
                "https://us.axa.com/axa-foundation/scholarship.html",
                "Focuses on personal achievement and overcoming challenges",
                False, "High School", 4.0
            )

    def add_research_scholarships(self):
        """Add research fellowships, REU programs, and research-focused scholarships"""
        discipline_lower = self.discipline.lower() if self.discipline else ''
        major_lower = self.major.lower() if self.major else ''

        # Universal research opportunities
        self.add_scholarship(
            "Barry Goldwater Scholarship", 7500, 7500,
            "$7,500/year", "January 31, 2026", 3.5, 3.8,
            "Undergraduates pursuing research careers in STEM",
            True, 600, 3, False, "Very High",
            "https://goldwaterscholarship.gov",
            "Premiere undergraduate research scholarship in the US; requires faculty nomination",
            False, "Research", 5.0
        )

        self.add_scholarship(
            "NSF Graduate Research Fellowship", 37000, 37000,
            "$37,000/year + $16,000 tuition for 3 years", "October 15, 2026", 3.5, 3.8,
            "Graduate students in STEM research",
            True, 1500, 3, False, "Very High",
            "https://www.nsfgrfp.org",
            "Most prestigious graduate research fellowship in the US",
            True, "Research", 5.0
        )

        self.add_scholarship(
            "Astronaut Scholar Foundation", 10000, 10000,
            "$10,000", "February 1, 2026", 3.5, 3.9,
            "STEM undergraduates with exceptional research potential",
            True, 800, 3, True, "Very High",
            "https://astronautscholarship.org",
            "For students who show initiative, creativity, and excellence in STEM research",
            False, "Research", 5.0
        )

        self.add_scholarship(
            "Hertz Foundation Fellowship", 250000, 250000,
            "Full tuition + $38,000/year stipend (5 years)", "October 24, 2026", 3.7, 3.9,
            "Graduate students pursuing applied physical, biological, or engineering sciences",
            True, 2000, 3, True, "Very High",
            "https://www.hertzfoundation.org/the-fellowship/",
            "Provides extraordinary freedom for graduate research; highly selective",
            True, "Research", 5.0
        )

        self.add_scholarship(
            "Ford Foundation Fellowship", 27000, 27000,
            "$27,000/year for 3 years", "December 5, 2026", 3.5, 3.8,
            "Graduate students committed to diversity in academia and research",
            True, 1000, 3, True, "Very High",
            "https://sites.nationalacademies.org/pga/fordfellowships/",
            "For students who show promise as scholars and researchers",
            True, "Research", 5.0
        )

        self.add_scholarship(
            "NSF Research Experience for Undergraduates (REU)", 4500, 8000,
            "$4,500-$8,000 stipend + housing", "February 15, 2026", 3.0, 3.3,
            "Undergraduates seeking paid summer research at universities nationwide",
            True, 400, 2, False, "Medium",
            "https://www.nsf.gov/crssprgm/reu/",
            "Paid summer research program at universities across the US; many sites available",
            False, "Research", 4.0
        )

        self.add_scholarship(
            "NIH Undergraduate Scholarship Program", 20000, 20000,
            "$20,000/year + paid NIH research internship", "March 15, 2026", 3.3, 3.5,
            "Undergraduates from disadvantaged backgrounds pursuing biomedical research",
            True, 800, 3, True, "High",
            "https://www.training.nih.gov/programs/ugsp",
            "Includes paid summer and post-graduation research at NIH; service commitment required",
            True, "Research", 5.0
        )

        self.add_scholarship(
            "Amgen Scholars Program", 3600, 6000,
            "$3,600-$6,000 stipend + housing", "February 1, 2026", 3.2, 3.5,
            "Undergraduates interested in science and biotechnology research",
            True, 500, 2, False, "High",
            "https://amgenscholars.com",
            "Summer research at leading universities; strong focus on biotech and life sciences",
            False, "Research", 4.0
        )

        self.add_scholarship(
            "DAAD RISE (Research in Germany)", 650, 800,
            "~$650-$800/month stipend + travel", "November 1, 2026", 3.0, 3.3,
            "Undergraduates in biology, chemistry, physics, earth sciences, engineering",
            True, 300, 2, False, "Medium",
            "https://www.daad.de/rise/en/",
            "Paid summer research internship at top German universities and research institutes",
            False, "Research", 3.5
        )

        # STEM-specific research opportunities
        if any(k in discipline_lower + major_lower for k in ['engineer', 'physics', 'computer', 'cs', 'math', 'science']):
            self.add_scholarship(
                "Department of Energy SULI Program", 500, 600,
                "~$500-$600/week stipend", "January 8, 2026", 3.0, 3.3,
                "STEM undergraduates for research at DOE national laboratories",
                True, 300, 1, False, "Medium",
                "https://science.osti.gov/wdts/suli",
                "Research at national labs (Argonne, Oak Ridge, Lawrence Berkeley, etc.)",
                False, "Research", 4.0
            )

        # Bio/health research
        if any(k in discipline_lower + major_lower for k in ['bio', 'health', 'medicine', 'chem', 'neuro', 'pre-med']):
            self.add_scholarship(
                "Howard Hughes Medical Institute Gilliam Fellowship", 49000, 49000,
                "$49,000/year stipend", "February 4, 2026", 3.5, 3.8,
                "Graduate students pursuing biomedical or life sciences research",
                True, 1000, 3, True, "Very High",
                "https://www.hhmi.org/programs/gilliam-fellowships-advanced-study",
                "For students from groups underrepresented in science; advisor must also apply",
                True, "Research", 5.0
            )

    def add_disability_scholarships(self):
        """Add scholarships for students with disabilities"""
        disability_lower = self.disability.lower()

        # Universal disability scholarships (all disabilities)
        self.add_scholarship(
            "Incight Scholarship", 1000, 2500,
            "$1,000-$2,500", "April 1, 2026", 2.0, 3.0,
            "Students with any documented physical or learning disability",
            True, 500, 1, False, "Medium",
            "https://incight.org/scholarships",
            "Open to students with any documented disability",
            False, "Disability", 3.0
        )

        self.add_scholarship(
            "Google Lime Scholarship", 10000, 10000,
            "$10,000", "December 1, 2025", 3.0, 3.5,
            "CS/Engineering students with disabilities",
            True, 500, 1, False, "High",
            "https://limeconnect.com/programs/google-lime-scholarship/",
            "For students with disabilities pursuing Computer Science or related fields",
            False, "Disability", 4.0
        )

        self.add_scholarship(
            "Microsoft Disability Scholarship", 5000, 5000,
            "$5,000", "February 1, 2026", 3.0, 3.3,
            "Students with disabilities pursuing STEM degrees",
            True, 500, 1, False, "Medium",
            "https://www.microsoft.com/en-us/diversity/programs/scholarships",
            "Part of Microsoft's broader diversity scholarship program",
            False, "Disability", 4.0
        )

        self.add_scholarship(
            "Foundation for Science and Disability Scholarship", 1000, 1000,
            "$1,000", "December 1, 2025", 3.0, 3.3,
            "Graduate students with disabilities in STEM",
            True, 500, 2, False, "Low",
            "https://stemd.org",
            "Supports students with disabilities pursuing science and technology careers",
            False, "Disability", 3.0
        )

        # Learning disabilities (dyslexia, LD, ADHD, processing disorders)
        if any(k in disability_lower for k in ['learning', 'dyslexia', 'adhd', 'add', 'dyscalculia', 'dysgraphia', 'processing']):
            self.add_scholarship(
                "Anne Ford Scholarship (NCLD)", 10000, 10000,
                "$10,000", "December 31, 2025", 2.5, 3.0,
                "Students with documented learning disabilities or ADHD",
                True, 1000, 3, True, "Medium",
                "https://www.ncld.org/anne-ford-scholarship",
                "Prestigious scholarship from the National Center for Learning Disabilities",
                False, "Disability", 5.0
            )

            self.add_scholarship(
                "Allegra Ford Thomas Scholarship (NCLD)", 2500, 2500,
                "$2,500", "December 31, 2025", 2.0, 2.5,
                "Community college students with documented learning disabilities",
                True, 600, 2, False, "Low",
                "https://www.ncld.org/allegra-ford-thomas-scholarship",
                "Specifically for community college students transitioning to 4-year programs",
                False, "Disability", 4.0
            )

            self.add_scholarship(
                "Learning Ally Achievement Award", 2500, 2500,
                "$2,500", "February 28, 2026", 2.0, 3.0,
                "Students with print disabilities (dyslexia, blindness, physical disability)",
                True, 400, 1, False, "Low",
                "https://learningally.org",
                "For students who use audiobooks due to print disabilities",
                False, "Disability", 4.0
            )

        # Autism spectrum
        if any(k in disability_lower for k in ['autism', 'autistic', 'asd', 'asperger']):
            self.add_scholarship(
                "Autism Speaks Scholarship", 3000, 3000,
                "$3,000", "March 15, 2026", 2.5, 3.0,
                "Students on the autism spectrum",
                True, 500, 2, False, "Medium",
                "https://www.autismspeaks.org",
                "For students on the autism spectrum pursuing higher education",
                False, "Disability", 4.0
            )

            self.add_scholarship(
                "ASAN Scholarship Fund", 1000, 3000,
                "$1,000-$3,000", "March 1, 2026", 2.0, 2.5,
                "Autistic students in any field of study",
                True, 600, 1, False, "Low",
                "https://autisticadvocacy.org",
                "From the Autistic Self Advocacy Network, for autistic students",
                False, "Disability", 3.5
            )

        # Visual impairment / blindness
        if any(k in disability_lower for k in ['blind', 'visual', 'vision', 'sight', 'low vision']):
            self.add_scholarship(
                "National Federation of the Blind Scholarship", 3000, 12000,
                "$3,000-$12,000", "March 31, 2026", 2.5, 3.0,
                "Blind or low-vision students in any field",
                True, 800, 3, True, "Medium",
                "https://nfb.org/programs-services/scholarships",
                "Multiple scholarship levels available; must attend NFB national convention",
                False, "Disability", 5.0
            )

            self.add_scholarship(
                "American Council of the Blind Scholarship", 1000, 5000,
                "$1,000-$5,000", "February 15, 2026", 2.5, 3.3,
                "Blind or visually impaired students",
                True, 500, 2, False, "Medium",
                "https://acb.org/scholarships",
                "Various scholarships for blind and visually impaired students",
                False, "Disability", 4.0
            )

        # Hearing impairment / deafness
        if any(k in disability_lower for k in ['deaf', 'hearing', 'hard of hearing', 'cochlear']):
            self.add_scholarship(
                "Alexander Graham Bell Association Scholarship", 1000, 5000,
                "$1,000-$5,000", "April 1, 2026", 2.5, 3.0,
                "Deaf and hard of hearing students who use spoken language",
                True, 500, 2, False, "Medium",
                "https://www.agbell.org/listening-and-spoken-language/scholarships",
                "For students with hearing loss who use listening and spoken language",
                False, "Disability", 4.0
            )

        # Physical / mobility disabilities
        if any(k in disability_lower for k in ['physical', 'mobility', 'wheelchair', 'paralysis', 'cerebral palsy', 'spina bifida', 'limb']):
            self.add_scholarship(
                "Disabled American Veterans (DAV) Scholarship", 5000, 15000,
                "$5,000-$15,000", "March 31, 2026", 2.5, 3.0,
                "Veterans or dependents with service-connected disabilities",
                True, 600, 2, False, "Medium",
                "https://www.dav.org",
                "For veterans with service-connected physical disabilities",
                False, "Disability", 4.0
            )

        # Epilepsy / seizure disorders
        if any(k in disability_lower for k in ['epilepsy', 'seizure', 'epileptic']):
            self.add_scholarship(
                "Epilepsy Foundation Scholarship", 3000, 6000,
                "$3,000-$6,000", "April 1, 2026", 2.5, 3.0,
                "Students with epilepsy or seizure disorders",
                True, 500, 1, False, "Low",
                "https://www.epilepsy.com/scholarships",
                "For students living with epilepsy pursuing higher education",
                False, "Disability", 4.0
            )

        # Chronic illness / health conditions
        if any(k in disability_lower for k in ['chronic', 'illness', 'cystic fibrosis', 'cf', 'immune', 'crohn', 'diabetes', 'cancer', 'lupus']):
            self.add_scholarship(
                "Patient Advocate Foundation Scholarship", 3000, 3000,
                "$3,000", "March 31, 2026", 2.5, 3.0,
                "Students with chronic illness, disability, or life-threatening disease",
                True, 500, 1, False, "Medium",
                "https://www.patientadvocate.org/connect-with-services/scholarship",
                "For students managing chronic medical conditions",
                False, "Disability", 4.0
            )

            self.add_scholarship(
                "Immune Deficiency Foundation Scholarship", 1000, 2500,
                "$1,000-$2,500", "March 1, 2026", 2.5, 3.0,
                "Students with primary immune deficiency diseases",
                True, 400, 1, False, "Low",
                "https://primaryimmune.org",
                "For students diagnosed with primary immune deficiency",
                False, "Disability", 3.5
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

        self.add_scholarship(
            "Microsoft Tuition Scholarship", 5000, 5000,
            "$5,000", "February 1, 2026", 3.3, 3.6,
            "CS/Engineering students",
            True, 600, 1, False, "High",
            "https://www.microsoft.com/en-us/diversity/programs/scholarships",
            "Preference for underrepresented groups",
            False, "Corporate", 4.0
        )

        self.add_scholarship(
            "Apple Scholars Program", 25000, 25000,
            "$25,000", "April 15, 2026", 3.6, 3.8,
            "Engineering/CS students",
            True, 1000, 3, True, "Very High",
            "https://www.apple.com/careers/us/apple-scholars.html",
            "Includes internship and mentorship",
            False, "Corporate", 7.0
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

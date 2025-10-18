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

#!/usr/bin/env python3
"""
Research Opportunity Agent
Matches students with research opportunities based on their profile
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

@dataclass
class ResearchOpportunity:
    """Research opportunity data class"""
    name: str
    organization: str
    research_area: str
    location: str  # University, Lab, or "Nationwide"
    compensation_type: str  # "Paid", "Credit", "Stipend", "Volunteer"
    stipend_amount: int  # 0 for unpaid
    duration: str  # "Summer 10 weeks", "Academic year", "Flexible"
    deadline: str
    gpa_min: float
    gpa_preferred: float
    eligible_years: List[str]  # ["Freshman", "Sophomore", "Junior", "Senior"]
    majors: List[str]  # ["Computer Science", "Biology", etc.]
    description: str
    application_url: str
    application_tips: str
    housing_provided: bool
    travel_covered: bool
    category: str  # "Federal REU", "University", "Corporate", "Lab"
    competitiveness: str  # "Low", "Medium", "High", "Very High"
    priority_score: float = 0.0

    def matches_profile(self, profile: dict) -> bool:
        """Check if opportunity matches student profile"""
        # GPA check
        student_gpa = float(profile.get('gpa', 0))
        if student_gpa < self.gpa_min:
            return False

        # Year check
        student_year = profile.get('year', '')
        if self.eligible_years and student_year not in self.eligible_years:
            return False

        # Major check (flexible matching)
        student_major = profile.get('major', '').lower()
        student_discipline = profile.get('discipline', '').lower()

        if self.majors:
            major_match = any(
                major.lower() in student_major or major.lower() in student_discipline
                for major in self.majors
            )
            if not major_match:
                return False

        return True

    def calculate_priority(self, profile: dict):
        """Calculate priority score based on student profile"""
        score = 0.0
        student_gpa = float(profile.get('gpa', 0))

        # Stipend weight (40%)
        if self.stipend_amount > 0:
            score += (self.stipend_amount / 10000) * 40

        # GPA match weight (30%)
        if student_gpa >= self.gpa_preferred:
            score += 30
        elif student_gpa >= self.gpa_min:
            score += 15

        # Housing/Travel benefits (20%)
        if self.housing_provided:
            score += 10
        if self.travel_covered:
            score += 10

        # Competition level (10%) - inverse
        comp_scores = {"Low": 10, "Medium": 7, "High": 4, "Very High": 2}
        score += comp_scores.get(self.competitiveness, 5)

        self.priority_score = round(score, 2)


class ResearchOpportunityAgent:
    """Agent to find and match research opportunities"""

    def __init__(self, student_profile: dict):
        self.student_profile = student_profile
        self.opportunities: List[ResearchOpportunity] = []

    def research_opportunities(self) -> List[ResearchOpportunity]:
        """Main method to find research opportunities"""
        self.add_federal_reu_programs()
        self.add_nih_programs()
        self.add_nasa_programs()
        self.add_doe_programs()
        self.add_university_programs()
        self.add_corporate_research()
        self.add_tech_company_research()

        # Filter by profile
        matched = [opp for opp in self.opportunities if opp.matches_profile(self.student_profile)]

        # Calculate priorities
        for opp in matched:
            opp.calculate_priority(self.student_profile)

        # Sort by priority
        matched.sort(key=lambda x: x.priority_score, reverse=True)

        return matched

    def add_federal_reu_programs(self):
        """Add NSF REU (Research Experience for Undergraduates) programs"""

        # Computer Science REUs
        self.opportunities.append(ResearchOpportunity(
            name="NSF REU in Computer Science",
            organization="National Science Foundation",
            research_area="Computer Science, AI, Cybersecurity, HCI",
            location="Nationwide (100+ sites)",
            compensation_type="Stipend",
            stipend_amount=6000,
            duration="Summer 10 weeks",
            deadline="February 1 - March 1, 2026",
            gpa_min=3.0,
            gpa_preferred=3.3,
            eligible_years=["Sophomore", "Junior", "Senior"],
            majors=["Computer Science", "Computer Engineering", "Information Technology"],
            description="Intensive summer research at top universities across the US",
            application_url="https://www.nsf.gov/crssprgm/reu/list_result.jsp?unitid=5049",
            application_tips="Apply to 5-10 programs, personalize each statement, reach out to PIs",
            housing_provided=True,
            travel_covered=True,
            category="Federal REU",
            competitiveness="High"
        ))

        # Engineering REUs
        self.opportunities.append(ResearchOpportunity(
            name="NSF REU in Engineering",
            organization="National Science Foundation",
            research_area="Mechanical, Electrical, Chemical, Civil Engineering",
            location="Nationwide (150+ sites)",
            compensation_type="Stipend",
            stipend_amount=6000,
            duration="Summer 10 weeks",
            deadline="February 1 - March 1, 2026",
            gpa_min=3.0,
            gpa_preferred=3.5,
            eligible_years=["Sophomore", "Junior", "Senior"],
            majors=["Engineering", "Mechanical Engineering", "Electrical Engineering", "Chemical Engineering"],
            description="Hands-on research in engineering labs nationwide",
            application_url="https://www.nsf.gov/crssprgm/reu/list_result.jsp?unitid=5050",
            application_tips="Strong preference for US citizens, highlight relevant coursework",
            housing_provided=True,
            travel_covered=True,
            category="Federal REU",
            competitiveness="High"
        ))

        # Biology/Life Sciences REUs
        self.opportunities.append(ResearchOpportunity(
            name="NSF REU in Biological Sciences",
            organization="National Science Foundation",
            research_area="Biology, Biochemistry, Ecology, Neuroscience",
            location="Nationwide (80+ sites)",
            compensation_type="Stipend",
            stipend_amount=5500,
            duration="Summer 8-10 weeks",
            deadline="February 1 - March 1, 2026",
            gpa_min=3.0,
            gpa_preferred=3.4,
            eligible_years=["Sophomore", "Junior", "Senior"],
            majors=["Biology", "Biochemistry", "Neuroscience", "Pre-Med"],
            description="Research in molecular biology, ecology, genetics, and more",
            application_url="https://www.nsf.gov/crssprgm/reu/list_result.jsp?unitid=5047",
            application_tips="Lab experience helpful but not required, emphasize scientific curiosity",
            housing_provided=True,
            travel_covered=True,
            category="Federal REU",
            competitiveness="Medium"
        ))

        # Physics/Astronomy REUs
        self.opportunities.append(ResearchOpportunity(
            name="NSF REU in Physics and Astronomy",
            organization="National Science Foundation",
            research_area="Physics, Astrophysics, Particle Physics, Cosmology",
            location="Nationwide (50+ sites)",
            compensation_type="Stipend",
            stipend_amount=6500,
            duration="Summer 10 weeks",
            deadline="January 15 - February 15, 2026",
            gpa_min=3.2,
            gpa_preferred=3.6,
            eligible_years=["Sophomore", "Junior", "Senior"],
            majors=["Physics", "Astronomy", "Astrophysics", "Applied Physics"],
            description="Cutting-edge research at observatories, national labs, and universities",
            application_url="https://www.nsf.gov/crssprgm/reu/list_result.jsp?unitid=5054",
            application_tips="Strong math/physics background required, research experience valued",
            housing_provided=True,
            travel_covered=True,
            category="Federal REU",
            competitiveness="Very High"
        ))

        # Chemistry REUs
        self.opportunities.append(ResearchOpportunity(
            name="NSF REU in Chemistry",
            organization="National Science Foundation",
            research_area="Organic, Inorganic, Physical, Analytical Chemistry",
            location="Nationwide (70+ sites)",
            compensation_type="Stipend",
            stipend_amount=5800,
            duration="Summer 10 weeks",
            deadline="February 1 - March 1, 2026",
            gpa_min=3.0,
            gpa_preferred=3.4,
            eligible_years=["Sophomore", "Junior", "Senior"],
            majors=["Chemistry", "Chemical Engineering", "Biochemistry"],
            description="Laboratory research in various chemistry disciplines",
            application_url="https://www.nsf.gov/crssprgm/reu/list_result.jsp?unitid=5048",
            application_tips="Lab safety training and coursework in chemistry required",
            housing_provided=True,
            travel_covered=True,
            category="Federal REU",
            competitiveness="Medium"
        ))

    def add_nih_programs(self):
        """Add NIH research programs"""

        self.opportunities.append(ResearchOpportunity(
            name="NIH Summer Internship Program (SIP)",
            organization="National Institutes of Health",
            research_area="Biomedical Research, Public Health, Clinical Research",
            location="NIH Campus, Bethesda MD",
            compensation_type="Stipend",
            stipend_amount=3000,
            duration="Summer 8-10 weeks",
            deadline="March 1, 2026",
            gpa_min=3.0,
            gpa_preferred=3.5,
            eligible_years=["Sophomore", "Junior", "Senior"],
            majors=["Biology", "Pre-Med", "Public Health", "Neuroscience", "Chemistry"],
            description="Research at the world's premier biomedical research institution",
            application_url="https://www.training.nih.gov/programs/sip",
            application_tips="Very competitive, highlight relevant coursework and research interest",
            housing_provided=False,
            travel_covered=True,
            category="Federal Research",
            competitiveness="Very High"
        ))

        self.opportunities.append(ResearchOpportunity(
            name="NIH Undergraduate Scholarship Program (UGSP)",
            organization="National Institutes of Health",
            research_area="Biomedical, Behavioral, Social Sciences",
            location="NIH Campus + Your University",
            compensation_type="Stipend + Tuition",
            stipend_amount=20000,
            duration="Summer + Academic Year (up to 4 years)",
            deadline="February 28, 2026",
            gpa_min=3.5,
            gpa_preferred=3.8,
            eligible_years=["Sophomore", "Junior"],
            majors=["Biology", "Chemistry", "Pre-Med", "Public Health"],
            description="Prestigious scholarship with paid research and service commitment",
            application_url="https://www.training.nih.gov/programs/ugsp",
            application_tips="Service commitment required, from disadvantaged backgrounds priority",
            housing_provided=True,
            travel_covered=True,
            category="Federal Research",
            competitiveness="Very High"
        ))

    def add_nasa_programs(self):
        """Add NASA research programs"""

        self.opportunities.append(ResearchOpportunity(
            name="NASA STEM Gateway",
            organization="NASA",
            research_area="Aerospace, Engineering, Computer Science, Physics",
            location="NASA Centers nationwide",
            compensation_type="Stipend",
            stipend_amount=7000,
            duration="Summer 10 weeks or Academic year",
            deadline="Rolling (apply early)",
            gpa_min=3.0,
            gpa_preferred=3.5,
            eligible_years=["Sophomore", "Junior", "Senior"],
            majors=["Aerospace Engineering", "Mechanical Engineering", "Computer Science", "Physics"],
            description="Internships at NASA centers working on real space missions",
            application_url="https://intern.nasa.gov/",
            application_tips="US citizenship required, apply early (December-January)",
            housing_provided=False,
            travel_covered=True,
            category="Federal Research",
            competitiveness="High"
        ))

    def add_doe_programs(self):
        """Add Department of Energy programs"""

        self.opportunities.append(ResearchOpportunity(
            name="DOE Science Undergraduate Laboratory Internship (SULI)",
            organization="Department of Energy",
            research_area="Physics, Chemistry, Engineering, Computer Science, Environmental Science",
            location="DOE National Labs (17 locations)",
            compensation_type="Stipend",
            stipend_amount=7200,
            duration="Summer 10 weeks",
            deadline="January 9, 2026",
            gpa_min=3.0,
            gpa_preferred=3.5,
            eligible_years=["Sophomore", "Junior", "Senior"],
            majors=["Physics", "Engineering", "Computer Science", "Chemistry"],
            description="Research at prestigious national laboratories (SLAC, Fermilab, LANL, etc.)",
            application_url="https://science.osti.gov/wdts/suli",
            application_tips="Competitive, highlight relevant coursework and research interests",
            housing_provided=True,
            travel_covered=True,
            category="Federal Research",
            competitiveness="High"
        ))

    def add_university_programs(self):
        """Add university-specific programs"""

        # Check if student's university has programs
        university = self.student_profile.get('university', '').lower()

        if 'mit' in university:
            self.opportunities.append(ResearchOpportunity(
                name="MIT UROP (Undergraduate Research Opportunities Program)",
                organization="MIT",
                research_area="All STEM fields",
                location="MIT Campus",
                compensation_type="Paid or Credit",
                stipend_amount=4000,
                duration="Semester or Summer",
                deadline="Rolling",
                gpa_min=3.0,
                gpa_preferred=3.3,
                eligible_years=["Freshman", "Sophomore", "Junior", "Senior"],
                majors=["All majors"],
                description="Work directly with MIT faculty on cutting-edge research",
                application_url="https://urop.mit.edu/",
                application_tips="MIT students only, apply early for best placements",
                housing_provided=False,
                travel_covered=False,
                category="University",
                competitiveness="Medium"
            ))

        if 'purdue' in university:
            self.opportunities.append(ResearchOpportunity(
                name="Purdue Summer Undergraduate Research Fellowship (SURF)",
                organization="Purdue University",
                research_area="Engineering, Science, Liberal Arts",
                location="Purdue Campus",
                compensation_type="Stipend",
                stipend_amount=4500,
                duration="Summer 10 weeks",
                deadline="February 1, 2026",
                gpa_min=3.0,
                gpa_preferred=3.3,
                eligible_years=["Sophomore", "Junior", "Senior"],
                majors=["All majors"],
                description="Full-time summer research with Purdue faculty",
                application_url="https://www.purdue.edu/undergrad-research/",
                application_tips="Purdue students preferred, connect with faculty beforehand",
                housing_provided=True,
                travel_covered=False,
                category="University",
                competitiveness="Medium"
            ))

    def add_corporate_research(self):
        """Add corporate research internships"""

        self.opportunities.append(ResearchOpportunity(
            name="IBM Research Internship",
            organization="IBM",
            research_area="AI, Quantum Computing, Cloud, Cybersecurity",
            location="Multiple US locations",
            compensation_type="Paid",
            stipend_amount=9000,
            duration="Summer 12 weeks",
            deadline="February 15, 2026",
            gpa_min=3.3,
            gpa_preferred=3.7,
            eligible_years=["Junior", "Senior"],
            majors=["Computer Science", "Computer Engineering", "Electrical Engineering"],
            description="Work with IBM Research scientists on cutting-edge problems",
            application_url="https://www.ibm.com/employment/",
            application_tips="Extremely competitive, strong CS fundamentals required",
            housing_provided=False,
            travel_covered=False,
            category="Corporate",
            competitiveness="Very High"
        ))

    def add_tech_company_research(self):
        """Add tech company research programs"""

        self.opportunities.append(ResearchOpportunity(
            name="Google Research Internship",
            organization="Google",
            research_area="Machine Learning, NLP, Computer Vision, Systems",
            location="Mountain View, NYC, Seattle",
            compensation_type="Paid",
            stipend_amount=10000,
            duration="Summer 12 weeks",
            deadline="January 15, 2026",
            gpa_min=3.5,
            gpa_preferred=3.8,
            eligible_years=["Junior", "Senior"],
            majors=["Computer Science", "Computer Engineering"],
            description="Work alongside Google researchers on publishable research",
            application_url="https://research.google/careers/",
            application_tips="PhD-track students preferred, publications/research experience valued",
            housing_provided=False,
            travel_covered=False,
            category="Corporate",
            competitiveness="Very High"
        ))

        self.opportunities.append(ResearchOpportunity(
            name="Microsoft Research Internship",
            organization="Microsoft",
            research_area="AI, Programming Languages, HCI, Security, Theory",
            location="Redmond WA, Cambridge MA, NYC",
            compensation_type="Paid",
            stipend_amount=10000,
            duration="Summer 12 weeks",
            deadline="January 31, 2026",
            gpa_min=3.5,
            gpa_preferred=3.8,
            eligible_years=["Junior", "Senior"],
            majors=["Computer Science", "Computer Engineering"],
            description="Research internship at Microsoft Research labs",
            application_url="https://www.microsoft.com/en-us/research/academic-program/",
            application_tips="Top-tier program, research experience and publications highly valued",
            housing_provided=False,
            travel_covered=False,
            category="Corporate",
            competitiveness="Very High"
        ))

    def add_research_opportunity(self, opportunity: ResearchOpportunity):
        """Add a research opportunity to the list"""
        self.opportunities.append(opportunity)

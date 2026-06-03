#!/usr/bin/env python3
"""
Research Opportunity Agent
Matches students with research opportunities based on their profile.

Author: Tim Smith
Note: All Code owned by Tim
"""

from dataclasses import dataclass, field
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
    # Optional identity / skill targeting (used for boosting and filtering)
    target_identities: List[str] = field(default_factory=list)
    # values like: "First-Gen", "URM", "Black", "Hispanic", "Native American",
    # "Pacific Islander", "Women", "LGBTQ+", "Disability", "Veteran", "International"
    skills_match: List[str] = field(default_factory=list)
    # values like: "Programming", "Research", "Leadership", "Writing"
    citizenship_required: bool = False
    priority_score: float = 0.0

    @staticmethod
    def _tokens(value) -> List[str]:
        if not value:
            return []
        if isinstance(value, list):
            return [str(v).strip().lower() for v in value if str(v).strip()]
        return [t.strip().lower() for t in str(value).split(",") if t.strip()]

    def matches_profile(self, profile: dict) -> bool:
        """Hard filters — return False to exclude this opportunity."""
        try:
            student_gpa = float(profile.get("gpa", 0))
        except (TypeError, ValueError):
            student_gpa = 0.0
        if student_gpa < self.gpa_min:
            return False

        student_year = (profile.get("year") or "").strip()
        if self.eligible_years and "All" not in self.eligible_years:
            if student_year and student_year not in self.eligible_years:
                return False

        student_major = (profile.get("major") or "").lower()
        student_discipline = (profile.get("discipline") or "").lower()
        if self.majors and not any(m.lower() == "all majors" for m in self.majors):
            major_match = any(
                m.lower() in student_major or m.lower() in student_discipline
                or (student_major and student_major in m.lower())
                for m in self.majors
            )
            if not major_match:
                return False

        if self.citizenship_required:
            residency = (profile.get("residency") or "").lower()
            if "international" in residency:
                return False

        return True

    def calculate_priority(self, profile: dict):
        """Priority score 0-100. Higher = better match."""
        score = 0.0
        try:
            student_gpa = float(profile.get("gpa", 0))
        except (TypeError, ValueError):
            student_gpa = 0.0

        # Stipend weight (up to 35)
        if self.stipend_amount > 0:
            score += min((self.stipend_amount / 10000) * 35, 35)

        # GPA match (up to 25)
        if student_gpa >= self.gpa_preferred:
            score += 25
        elif student_gpa >= self.gpa_min:
            score += 12

        # Housing/Travel (up to 15)
        if self.housing_provided:
            score += 8
        if self.travel_covered:
            score += 7

        # Competition (up to 10) — inverse
        comp_scores = {"Low": 10, "Medium": 7, "High": 4, "Very High": 2}
        score += comp_scores.get(self.competitiveness, 5)

        # Identity boost (up to 15)
        if self.target_identities:
            identity_hits = 0
            heritage_tokens = self._tokens(profile.get("heritage"))
            disability_tokens = self._tokens(profile.get("disability"))
            gender = (profile.get("gender") or "").lower()
            urm_terms = {
                "black", "african american", "hispanic", "latino", "latina",
                "native american", "indigenous", "pacific islander", "alaska native",
            }
            is_urm = any(t in urm_terms or any(u in t for u in urm_terms) for t in heritage_tokens)

            for tag in self.target_identities:
                tag_l = tag.lower()
                if tag_l == "first-gen" and profile.get("first_gen"):
                    identity_hits += 1
                elif tag_l == "urm" and is_urm:
                    identity_hits += 1
                elif tag_l in {"black", "hispanic", "native american", "pacific islander", "asian american"}:
                    if any(tag_l in t or t in tag_l for t in heritage_tokens):
                        identity_hits += 1
                elif tag_l in {"women", "female"} and gender in {"female", "non-binary"}:
                    identity_hits += 1
                elif tag_l == "lgbtq+" and gender in {"lgbtq+", "non-binary"}:
                    identity_hits += 1
                elif tag_l == "disability" and disability_tokens:
                    identity_hits += 1
                elif tag_l == "veteran" and profile.get("military"):
                    identity_hits += 1

            score += min(identity_hits * 8, 15)

        # Skill boost (up to 5)
        if self.skills_match:
            skill_tokens = self._tokens(profile.get("skills"))
            if any(any(s.lower() in t or t in s.lower() for t in skill_tokens) for s in self.skills_match):
                score += 5

        self.priority_score = round(min(score, 100), 2)


class ResearchOpportunityAgent:
    """Agent to find and match research opportunities"""

    def __init__(self, student_profile: dict):
        self.student_profile = student_profile
        self.opportunities: List[ResearchOpportunity] = []

    def research_opportunities(self) -> List[ResearchOpportunity]:
        self.add_federal_reu_programs()
        self.add_nih_programs()
        self.add_nasa_programs()
        self.add_doe_programs()
        self.add_other_federal_programs()
        self.add_identity_focused_programs()
        self.add_university_programs()
        self.add_corporate_research()
        self.add_tech_company_research()
        self.add_international_programs()

        # Merit-based only: exclude identity/need-restricted programs (e.g.
        # McNair, LSAMP, NIH UGSP). These are gated on first-gen / low-income /
        # URM status by design, and the profile collects no such financial data,
        # so they can't be matched reliably. target_identities is set precisely
        # on those programs and empty on every merit-open one.
        merit_only = [o for o in self.opportunities if not o.target_identities]
        matched = [o for o in merit_only if o.matches_profile(self.student_profile)]
        for opp in matched:
            opp.calculate_priority(self.student_profile)
        matched.sort(key=lambda x: x.priority_score, reverse=True)
        return matched

    def add_federal_reu_programs(self):
        self.opportunities.extend([
            ResearchOpportunity(
                name="NSF REU in Computer Science",
                organization="National Science Foundation",
                research_area="Computer Science, AI, Cybersecurity, HCI",
                location="Nationwide (100+ sites)",
                compensation_type="Stipend", stipend_amount=6000,
                duration="Summer 10 weeks",
                deadline="February 1 - March 1, 2026",
                gpa_min=3.0, gpa_preferred=3.3,
                eligible_years=["Sophomore", "Junior", "Senior"],
                majors=["Computer Science", "Computer Engineering", "Information Technology"],
                description="Intensive summer research at top universities across the US",
                application_url="https://www.nsf.gov/crssprgm/reu/list_result.jsp?unitid=5049",
                application_tips="Apply to 5-10 programs, personalize each statement, reach out to PIs",
                housing_provided=True, travel_covered=True,
                category="Federal REU", competitiveness="High",
                skills_match=["Programming", "Research"], citizenship_required=True,
            ),
            ResearchOpportunity(
                name="NSF REU in Engineering",
                organization="National Science Foundation",
                research_area="Mechanical, Electrical, Chemical, Civil Engineering",
                location="Nationwide (150+ sites)",
                compensation_type="Stipend", stipend_amount=6000,
                duration="Summer 10 weeks",
                deadline="February 1 - March 1, 2026",
                gpa_min=3.0, gpa_preferred=3.5,
                eligible_years=["Sophomore", "Junior", "Senior"],
                majors=["Engineering", "Mechanical Engineering", "Electrical Engineering", "Chemical Engineering"],
                description="Hands-on research in engineering labs nationwide",
                application_url="https://www.nsf.gov/crssprgm/reu/list_result.jsp?unitid=5050",
                application_tips="Strong preference for US citizens, highlight relevant coursework",
                housing_provided=True, travel_covered=True,
                category="Federal REU", competitiveness="High",
                skills_match=["Research", "Design"], citizenship_required=True,
            ),
            ResearchOpportunity(
                name="NSF REU in Biological Sciences",
                organization="National Science Foundation",
                research_area="Biology, Biochemistry, Ecology, Neuroscience",
                location="Nationwide (80+ sites)",
                compensation_type="Stipend", stipend_amount=5500,
                duration="Summer 8-10 weeks",
                deadline="February 1 - March 1, 2026",
                gpa_min=3.0, gpa_preferred=3.4,
                eligible_years=["Sophomore", "Junior", "Senior"],
                majors=["Biology", "Biochemistry", "Neuroscience", "Pre-Med"],
                description="Research in molecular biology, ecology, genetics, and more",
                application_url="https://www.nsf.gov/crssprgm/reu/list_result.jsp?unitid=5047",
                application_tips="Lab experience helpful but not required, emphasize scientific curiosity",
                housing_provided=True, travel_covered=True,
                category="Federal REU", competitiveness="Medium",
                skills_match=["Research"], citizenship_required=True,
            ),
            ResearchOpportunity(
                name="NSF REU in Physics and Astronomy",
                organization="National Science Foundation",
                research_area="Physics, Astrophysics, Particle Physics, Cosmology",
                location="Nationwide (50+ sites)",
                compensation_type="Stipend", stipend_amount=6500,
                duration="Summer 10 weeks",
                deadline="January 15 - February 15, 2026",
                gpa_min=3.2, gpa_preferred=3.6,
                eligible_years=["Sophomore", "Junior", "Senior"],
                majors=["Physics", "Astronomy", "Astrophysics", "Applied Physics"],
                description="Cutting-edge research at observatories, national labs, and universities",
                application_url="https://www.nsf.gov/crssprgm/reu/list_result.jsp?unitid=5054",
                application_tips="Strong math/physics background required, research experience valued",
                housing_provided=True, travel_covered=True,
                category="Federal REU", competitiveness="Very High",
                skills_match=["Research"], citizenship_required=True,
            ),
            ResearchOpportunity(
                name="NSF REU in Chemistry",
                organization="National Science Foundation",
                research_area="Organic, Inorganic, Physical, Analytical Chemistry",
                location="Nationwide (70+ sites)",
                compensation_type="Stipend", stipend_amount=5800,
                duration="Summer 10 weeks",
                deadline="February 1 - March 1, 2026",
                gpa_min=3.0, gpa_preferred=3.4,
                eligible_years=["Sophomore", "Junior", "Senior"],
                majors=["Chemistry", "Chemical Engineering", "Biochemistry"],
                description="Laboratory research in various chemistry disciplines",
                application_url="https://www.nsf.gov/crssprgm/reu/list_result.jsp?unitid=5048",
                application_tips="Lab safety training and coursework in chemistry required",
                housing_provided=True, travel_covered=True,
                category="Federal REU", competitiveness="Medium",
                skills_match=["Research"], citizenship_required=True,
            ),
            ResearchOpportunity(
                name="NSF REU in Mathematics",
                organization="National Science Foundation",
                research_area="Pure Math, Applied Math, Statistics, Data Science",
                location="Nationwide (60+ sites)",
                compensation_type="Stipend", stipend_amount=5500,
                duration="Summer 8-10 weeks",
                deadline="February 1 - March 1, 2026",
                gpa_min=3.2, gpa_preferred=3.6,
                eligible_years=["Sophomore", "Junior", "Senior"],
                majors=["Mathematics", "Statistics", "Applied Mathematics", "Data Science"],
                description="Independent and group research projects in mathematics",
                application_url="https://www.nsf.gov/crssprgm/reu/list_result.jsp?unitid=5044",
                application_tips="Highlight proof-writing experience and advanced coursework",
                housing_provided=True, travel_covered=True,
                category="Federal REU", competitiveness="High",
                skills_match=["Research"], citizenship_required=True,
            ),
        ])

    def add_nih_programs(self):
        self.opportunities.extend([
            ResearchOpportunity(
                name="NIH Summer Internship Program (SIP)",
                organization="National Institutes of Health",
                research_area="Biomedical Research, Public Health, Clinical Research",
                location="NIH Campus, Bethesda MD",
                compensation_type="Stipend", stipend_amount=3000,
                duration="Summer 8-10 weeks",
                deadline="March 1, 2026",
                gpa_min=3.0, gpa_preferred=3.5,
                eligible_years=["Sophomore", "Junior", "Senior"],
                majors=["Biology", "Pre-Med", "Public Health", "Neuroscience", "Chemistry"],
                description="Research at the world's premier biomedical research institution",
                application_url="https://www.training.nih.gov/programs/sip",
                application_tips="Very competitive, highlight relevant coursework and research interest",
                housing_provided=False, travel_covered=True,
                category="Federal Research", competitiveness="Very High",
                skills_match=["Research"], citizenship_required=False,
            ),
            ResearchOpportunity(
                name="NIH Undergraduate Scholarship Program (UGSP)",
                organization="National Institutes of Health",
                research_area="Biomedical, Behavioral, Social Sciences",
                location="NIH Campus + Your University",
                compensation_type="Stipend + Tuition", stipend_amount=20000,
                duration="Summer + Academic Year (up to 4 years)",
                deadline="February 28, 2026",
                gpa_min=3.5, gpa_preferred=3.8,
                eligible_years=["Sophomore", "Junior"],
                majors=["Biology", "Chemistry", "Pre-Med", "Public Health"],
                description="Prestigious scholarship with paid research and service commitment",
                application_url="https://www.training.nih.gov/programs/ugsp",
                application_tips="Service commitment required; priority to disadvantaged backgrounds",
                housing_provided=True, travel_covered=True,
                category="Federal Research", competitiveness="Very High",
                target_identities=["First-Gen", "URM"],
                skills_match=["Research"], citizenship_required=True,
            ),
            ResearchOpportunity(
                name="MARC U-STAR (Maximizing Access to Research Careers)",
                organization="NIH / NIGMS",
                research_area="Biomedical, Behavioral Research",
                location="Participating universities nationwide",
                compensation_type="Stipend + Tuition", stipend_amount=12000,
                duration="2 years (Junior + Senior)",
                deadline="Varies by campus (typically spring of Sophomore year)",
                gpa_min=3.2, gpa_preferred=3.5,
                eligible_years=["Sophomore"],
                majors=["Biology", "Chemistry", "Biochemistry", "Neuroscience", "Public Health"],
                description="Honors program preparing URM students for biomedical PhD programs",
                application_url="https://www.nigms.nih.gov/training/marc",
                application_tips="Must attend a participating institution; research experience and commitment to PhD valued",
                housing_provided=False, travel_covered=False,
                category="Identity-Focused", competitiveness="High",
                target_identities=["URM", "Black", "Hispanic", "Native American", "Pacific Islander"],
                citizenship_required=True,
            ),
        ])

    def add_nasa_programs(self):
        self.opportunities.extend([
            ResearchOpportunity(
                name="NASA STEM Gateway Internships",
                organization="NASA",
                research_area="Aerospace, Engineering, Computer Science, Physics",
                location="NASA Centers nationwide",
                compensation_type="Stipend", stipend_amount=7000,
                duration="Summer 10 weeks or Academic year",
                deadline="Rolling (apply early - February deadline for summer)",
                gpa_min=3.0, gpa_preferred=3.5,
                eligible_years=["Sophomore", "Junior", "Senior"],
                majors=["Aerospace Engineering", "Mechanical Engineering", "Computer Science", "Physics"],
                description="Internships at NASA centers working on real space missions",
                application_url="https://intern.nasa.gov/",
                application_tips="US citizenship required, apply early (December-January)",
                housing_provided=False, travel_covered=True,
                category="Federal Research", competitiveness="High",
                skills_match=["Programming", "Research", "Design"], citizenship_required=True,
            ),
            ResearchOpportunity(
                name="NASA Pathways Program",
                organization="NASA",
                research_area="Engineering, Science, IT, Business",
                location="Multiple NASA centers",
                compensation_type="Paid", stipend_amount=15000,
                duration="Multi-semester (paid co-op with conversion to full-time)",
                deadline="Rolling - check USAJOBS",
                gpa_min=3.0, gpa_preferred=3.4,
                eligible_years=["Sophomore", "Junior", "Senior"],
                majors=["Engineering", "Computer Science", "Mathematics", "Physics"],
                description="Pathways co-op leading to full-time NASA employment",
                application_url="https://www.usajobs.gov/Search/Results?l=&k=NASA%20Pathways",
                application_tips="Apply through USAJOBS; multi-tour commitment expected",
                housing_provided=False, travel_covered=False,
                category="Federal Research", competitiveness="High",
                citizenship_required=True,
            ),
        ])

    def add_doe_programs(self):
        self.opportunities.extend([
            ResearchOpportunity(
                name="DOE Science Undergraduate Laboratory Internship (SULI)",
                organization="Department of Energy",
                research_area="Physics, Chemistry, Engineering, Computer Science, Environmental Science",
                location="DOE National Labs (17 locations)",
                compensation_type="Stipend", stipend_amount=7200,
                duration="Summer 10 weeks",
                deadline="January 9, 2026",
                gpa_min=3.0, gpa_preferred=3.5,
                eligible_years=["Sophomore", "Junior", "Senior"],
                majors=["Physics", "Engineering", "Computer Science", "Chemistry"],
                description="Research at prestigious national laboratories (SLAC, Fermilab, LANL, etc.)",
                application_url="https://science.osti.gov/wdts/suli",
                application_tips="Competitive, highlight relevant coursework and research interests",
                housing_provided=True, travel_covered=True,
                category="Federal Research", competitiveness="High",
                skills_match=["Research", "Programming"], citizenship_required=True,
            ),
            ResearchOpportunity(
                name="DOE Community College Internships (CCI)",
                organization="Department of Energy",
                research_area="Applied Science, Engineering, Tech",
                location="DOE National Labs",
                compensation_type="Stipend", stipend_amount=6500,
                duration="Summer 10 weeks",
                deadline="January 9, 2026",
                gpa_min=3.0, gpa_preferred=3.3,
                eligible_years=["Freshman", "Sophomore"],
                majors=["Engineering", "Physics", "Chemistry", "Computer Science"],
                description="Technical internships for community college students at national labs",
                application_url="https://science.osti.gov/wdts/cci",
                application_tips="Community college students preferred",
                housing_provided=True, travel_covered=True,
                category="Federal Research", competitiveness="Medium",
                citizenship_required=True,
            ),
        ])

    def add_other_federal_programs(self):
        self.opportunities.extend([
            ResearchOpportunity(
                name="NIST Summer Undergraduate Research Fellowship (SURF)",
                organization="National Institute of Standards and Technology",
                research_area="Materials, Physics, Chemistry, Engineering, Computer Science",
                location="Gaithersburg MD, Boulder CO",
                compensation_type="Stipend", stipend_amount=6500,
                duration="Summer 11 weeks",
                deadline="February 15, 2026",
                gpa_min=3.0, gpa_preferred=3.5,
                eligible_years=["Sophomore", "Junior", "Senior"],
                majors=["Physics", "Chemistry", "Engineering", "Computer Science", "Mathematics"],
                description="Research with NIST scientists on measurement science and standards",
                application_url="https://www.nist.gov/surf",
                application_tips="Strong technical writing in personal statement is key",
                housing_provided=True, travel_covered=True,
                category="Federal Research", competitiveness="High",
                skills_match=["Research"], citizenship_required=True,
            ),
            ResearchOpportunity(
                name="NOAA Ernest F. Hollings Scholarship",
                organization="NOAA",
                research_area="Oceanography, Atmospheric Sciences, Climate, Marine Biology",
                location="NOAA facilities nationwide",
                compensation_type="Stipend + Tuition", stipend_amount=9500,
                duration="Summer 10 weeks + Academic year tuition ($9,500/yr)",
                deadline="January 31, 2026",
                gpa_min=3.0, gpa_preferred=3.5,
                eligible_years=["Sophomore"],
                majors=["Oceanography", "Marine Biology", "Atmospheric Sciences", "Environmental Science", "Biology"],
                description="2-year scholarship with paid NOAA internship",
                application_url="https://www.noaa.gov/office-education/hollings-scholarship",
                application_tips="Sophomores only; demonstrate environmental/ocean interest",
                housing_provided=False, travel_covered=True,
                category="Federal Research", competitiveness="High",
                citizenship_required=True,
            ),
            ResearchOpportunity(
                name="USDA REEU (Research and Extension Experiences for Undergraduates)",
                organization="USDA / NIFA",
                research_area="Agriculture, Food Science, Natural Resources, Environmental Science",
                location="Land-grant universities nationwide",
                compensation_type="Stipend", stipend_amount=5000,
                duration="Summer 8-10 weeks",
                deadline="February - March 2026 (varies by site)",
                gpa_min=2.8, gpa_preferred=3.3,
                eligible_years=["Freshman", "Sophomore", "Junior", "Senior"],
                majors=["Agriculture", "Food Science", "Biology", "Environmental Science", "Animal Science"],
                description="Hands-on research in food, agriculture, and natural resources",
                application_url="https://www.nifa.usda.gov/grants/programs/reeu",
                application_tips="Often less competitive than NSF REU; great gateway for first research experience",
                housing_provided=True, travel_covered=False,
                category="Federal Research", competitiveness="Medium",
                skills_match=["Research"], citizenship_required=False,
            ),
            ResearchOpportunity(
                name="Naval Research Enterprise Internship Program (NREIP)",
                organization="U.S. Navy / ONR",
                research_area="Engineering, Computer Science, Physics, Math, Chemistry",
                location="Navy labs (NRL, NSWC, NUWC, etc.)",
                compensation_type="Stipend", stipend_amount=7500,
                duration="Summer 10 weeks",
                deadline="October 30, 2025 (annual cycle)",
                gpa_min=3.0, gpa_preferred=3.5,
                eligible_years=["Sophomore", "Junior", "Senior"],
                majors=["Engineering", "Computer Science", "Physics", "Chemistry", "Mathematics"],
                description="Defense-oriented research at U.S. Navy laboratories",
                application_url="https://nreip.asee.org/",
                application_tips="Apply early; security clearance not required but background check is",
                housing_provided=False, travel_covered=False,
                category="Federal Research", competitiveness="Medium",
                citizenship_required=True,
            ),
            ResearchOpportunity(
                name="Smithsonian Institution Internship Program",
                organization="Smithsonian Institution",
                research_area="Natural History, Anthropology, Art History, Astrophysics",
                location="Washington DC, NYC, Panama, others",
                compensation_type="Stipend", stipend_amount=6000,
                duration="10-12 weeks (Summer, Fall, Spring)",
                deadline="February 1, 2026 for summer",
                gpa_min=3.0, gpa_preferred=3.4,
                eligible_years=["Sophomore", "Junior", "Senior"],
                majors=["Biology", "History", "Anthropology", "Art History", "Physics", "Environmental Science"],
                description="Research at Smithsonian museums and research centers",
                application_url="https://internships.si.edu/",
                application_tips="Many opportunities — match interests to specific museum/center",
                housing_provided=False, travel_covered=False,
                category="Federal Research", competitiveness="Medium",
            ),
        ])

    def add_identity_focused_programs(self):
        self.opportunities.extend([
            ResearchOpportunity(
                name="McNair Scholars Program",
                organization="U.S. Department of Education / Host Universities",
                research_area="All disciplines (PhD preparation)",
                location="200+ host universities",
                compensation_type="Stipend", stipend_amount=3000,
                duration="Summer 8 weeks + Academic year mentoring",
                deadline="Varies by campus (usually spring sophomore/junior year)",
                gpa_min=3.0, gpa_preferred=3.3,
                eligible_years=["Sophomore", "Junior"],
                majors=["All majors"],
                description="Research and grad school prep for first-gen, low-income, and URM students",
                application_url="https://mcnairscholars.com/",
                application_tips="Must be first-gen + low-income OR URM; check if your school has a chapter",
                housing_provided=False, travel_covered=True,
                category="Identity-Focused", competitiveness="Medium",
                target_identities=["First-Gen", "URM"],
                skills_match=["Research"], citizenship_required=True,
            ),
            ResearchOpportunity(
                name="LSAMP (Louis Stokes Alliances for Minority Participation)",
                organization="National Science Foundation",
                research_area="STEM (broadly)",
                location="60+ LSAMP alliance campuses",
                compensation_type="Stipend", stipend_amount=4000,
                duration="Summer + Academic year support",
                deadline="Varies by alliance (typically spring)",
                gpa_min=2.8, gpa_preferred=3.2,
                eligible_years=["Freshman", "Sophomore", "Junior", "Senior"],
                majors=["Engineering", "Computer Science", "Biology", "Chemistry", "Physics", "Mathematics"],
                description="Mentoring, research, and support for URM students in STEM",
                application_url="https://www.lsamp.org/",
                application_tips="Must attend an LSAMP alliance institution",
                housing_provided=False, travel_covered=False,
                category="Identity-Focused", competitiveness="Medium",
                target_identities=["URM", "Black", "Hispanic", "Native American", "Pacific Islander"],
            ),
            ResearchOpportunity(
                name="Big Ten SROP (Summer Research Opportunities Program)",
                organization="Big Ten Academic Alliance",
                research_area="All disciplines",
                location="Big Ten universities (Michigan, Illinois, Purdue, etc.)",
                compensation_type="Stipend", stipend_amount=5000,
                duration="Summer 8-10 weeks",
                deadline="February 1, 2026",
                gpa_min=3.0, gpa_preferred=3.4,
                eligible_years=["Sophomore", "Junior"],
                majors=["All majors"],
                description="Faculty-mentored research at Big Ten universities; PhD prep focus",
                application_url="https://www.btaa.org/resources-for/students/srop/introduction",
                application_tips="Strong emphasis on URM and first-gen students; reach out to faculty mentors",
                housing_provided=True, travel_covered=True,
                category="Identity-Focused", competitiveness="High",
                target_identities=["URM", "First-Gen"],
            ),
            ResearchOpportunity(
                name="MIT Summer Research Program (MSRP)",
                organization="MIT",
                research_area="Science and Engineering",
                location="MIT Campus",
                compensation_type="Stipend", stipend_amount=7000,
                duration="Summer 9 weeks",
                deadline="January 12, 2026",
                gpa_min=3.5, gpa_preferred=3.7,
                eligible_years=["Sophomore", "Junior"],
                majors=["Engineering", "Computer Science", "Biology", "Chemistry", "Physics", "Mathematics"],
                description="MIT research program with strong URM/disadvantaged student focus",
                application_url="https://oge.mit.edu/msrp/",
                application_tips="Highly selective; non-MIT undergrads from underrepresented backgrounds",
                housing_provided=True, travel_covered=True,
                category="Identity-Focused", competitiveness="Very High",
                target_identities=["URM", "First-Gen"],
                skills_match=["Research"],
            ),
            ResearchOpportunity(
                name="SACNAS National Diversity in STEM Conference",
                organization="SACNAS",
                research_area="All STEM",
                location="Annual conference (rotating US city)",
                compensation_type="Travel award (~$1,500)", stipend_amount=1500,
                duration="3-day conference + research presentation",
                deadline="July 2026 for fall conference",
                gpa_min=2.5, gpa_preferred=3.0,
                eligible_years=["Freshman", "Sophomore", "Junior", "Senior"],
                majors=["All majors"],
                description="Present research, network with grad programs targeting Chicano/Hispanic/Native American students",
                application_url="https://www.sacnas.org/conference",
                application_tips="Travel awards competitive; abstract submission strengthens application",
                housing_provided=False, travel_covered=True,
                category="Identity-Focused", competitiveness="Low",
                target_identities=["Hispanic", "Native American", "URM"],
            ),
            ResearchOpportunity(
                name="SWE Collegiate Leadership Institute / Research Awards",
                organization="Society of Women Engineers",
                research_area="All Engineering disciplines",
                location="Varies",
                compensation_type="Travel award + Research support", stipend_amount=2000,
                duration="Summer or Academic year",
                deadline="February 15, 2026",
                gpa_min=3.0, gpa_preferred=3.4,
                eligible_years=["Sophomore", "Junior", "Senior"],
                majors=["Engineering", "Computer Science", "Computer Engineering"],
                description="Research stipends and conference travel for women in engineering",
                application_url="https://swe.org/scholarships/",
                application_tips="SWE membership encouraged; emphasize leadership in WE-affinity orgs",
                housing_provided=False, travel_covered=True,
                category="Identity-Focused", competitiveness="Medium",
                target_identities=["Women"],
            ),
        ])

    def add_university_programs(self):
        university = (self.student_profile.get("university") or "").lower()

        if "mit" in university:
            self.opportunities.append(ResearchOpportunity(
                name="MIT UROP (Undergraduate Research Opportunities Program)",
                organization="MIT",
                research_area="All STEM fields",
                location="MIT Campus",
                compensation_type="Paid or Credit", stipend_amount=4000,
                duration="Semester or Summer", deadline="Rolling",
                gpa_min=3.0, gpa_preferred=3.3,
                eligible_years=["Freshman", "Sophomore", "Junior", "Senior"],
                majors=["All majors"],
                description="Work directly with MIT faculty on cutting-edge research",
                application_url="https://urop.mit.edu/",
                application_tips="MIT students only, apply early for best placements",
                housing_provided=False, travel_covered=False,
                category="University", competitiveness="Medium",
            ))

        if "purdue" in university:
            self.opportunities.append(ResearchOpportunity(
                name="Purdue Summer Undergraduate Research Fellowship (SURF)",
                organization="Purdue University",
                research_area="Engineering, Science, Liberal Arts",
                location="Purdue Campus",
                compensation_type="Stipend", stipend_amount=4500,
                duration="Summer 10 weeks", deadline="February 1, 2026",
                gpa_min=3.0, gpa_preferred=3.3,
                eligible_years=["Sophomore", "Junior", "Senior"],
                majors=["All majors"],
                description="Full-time summer research with Purdue faculty",
                application_url="https://www.purdue.edu/undergrad-research/",
                application_tips="Purdue students preferred, connect with faculty beforehand",
                housing_provided=True, travel_covered=False,
                category="University", competitiveness="Medium",
            ))

        if "caltech" in university:
            self.opportunities.append(ResearchOpportunity(
                name="Caltech SURF (Summer Undergraduate Research Fellowships)",
                organization="Caltech",
                research_area="All sciences and engineering",
                location="Caltech Campus, Pasadena CA",
                compensation_type="Stipend", stipend_amount=7500,
                duration="Summer 10 weeks", deadline="February 22, 2026",
                gpa_min=3.3, gpa_preferred=3.6,
                eligible_years=["Sophomore", "Junior", "Senior"],
                majors=["All majors"],
                description="Independent research project mentored by Caltech faculty",
                application_url="https://sfp.caltech.edu/programs/surf",
                application_tips="Self-proposed projects scored highly; write a detailed proposal",
                housing_provided=True, travel_covered=False,
                category="University", competitiveness="High",
                skills_match=["Research"],
            ))

        if "stanford" in university:
            self.opportunities.append(ResearchOpportunity(
                name="Stanford Summer Research Program (SSRP)",
                organization="Stanford University",
                research_area="Biosciences, Engineering, Humanities",
                location="Stanford Campus",
                compensation_type="Stipend", stipend_amount=7000,
                duration="Summer 9 weeks", deadline="February 9, 2026",
                gpa_min=3.3, gpa_preferred=3.6,
                eligible_years=["Sophomore", "Junior"],
                majors=["All majors"],
                description="Mentored research and grad school preparation",
                application_url="https://undergradresearch.stanford.edu/",
                application_tips="Strong focus on URM students from non-Stanford institutions",
                housing_provided=True, travel_covered=True,
                category="University", competitiveness="Very High",
                target_identities=["URM", "First-Gen"],
            ))

        if "harvard" in university:
            self.opportunities.append(ResearchOpportunity(
                name="Harvard PRISE (Program for Research in Science and Engineering)",
                organization="Harvard University",
                research_area="Science, Engineering, Math",
                location="Harvard Campus",
                compensation_type="Stipend", stipend_amount=4500,
                duration="Summer 10 weeks", deadline="February 7, 2026",
                gpa_min=3.5, gpa_preferred=3.7,
                eligible_years=["Sophomore", "Junior"],
                majors=["All majors"],
                description="Residential research community for Harvard undergrads",
                application_url="https://uraf.harvard.edu/prise",
                application_tips="Harvard students only; identify Harvard faculty mentor first",
                housing_provided=True, travel_covered=False,
                category="University", competitiveness="High",
            ))

        if "berkeley" in university:
            self.opportunities.append(ResearchOpportunity(
                name="UC Berkeley SURF (Summer Undergraduate Research Fellowships)",
                organization="UC Berkeley",
                research_area="All disciplines",
                location="UC Berkeley Campus",
                compensation_type="Stipend", stipend_amount=5000,
                duration="Summer 8-10 weeks", deadline="February 6, 2026",
                gpa_min=3.0, gpa_preferred=3.3,
                eligible_years=["Sophomore", "Junior", "Senior"],
                majors=["All majors"],
                description="Independent research with Berkeley faculty mentor",
                application_url="https://research.berkeley.edu/surf",
                application_tips="Berkeley students; proposal-driven; build relationship with faculty mentor",
                housing_provided=False, travel_covered=False,
                category="University", competitiveness="Medium",
            ))

    def add_corporate_research(self):
        self.opportunities.extend([
            ResearchOpportunity(
                name="IBM Research Internship",
                organization="IBM",
                research_area="AI, Quantum Computing, Cloud, Cybersecurity",
                location="Multiple US locations",
                compensation_type="Paid", stipend_amount=9000,
                duration="Summer 12 weeks", deadline="February 15, 2026",
                gpa_min=3.3, gpa_preferred=3.7,
                eligible_years=["Junior", "Senior"],
                majors=["Computer Science", "Computer Engineering", "Electrical Engineering"],
                description="Work with IBM Research scientists on cutting-edge problems",
                application_url="https://www.ibm.com/employment/",
                application_tips="Extremely competitive, strong CS fundamentals required",
                housing_provided=False, travel_covered=False,
                category="Corporate", competitiveness="Very High",
                skills_match=["Programming", "Research"],
            ),
            ResearchOpportunity(
                name="Amgen Scholars Program",
                organization="Amgen Foundation",
                research_area="Biotechnology, Biomedical, Pharmacology",
                location="Caltech, Harvard, Stanford, Columbia, UCSF, others",
                compensation_type="Stipend", stipend_amount=4500,
                duration="Summer 8-10 weeks", deadline="February 1, 2026",
                gpa_min=3.2, gpa_preferred=3.6,
                eligible_years=["Sophomore", "Junior"],
                majors=["Biology", "Biochemistry", "Chemistry", "Bioengineering", "Pre-Med"],
                description="Biotechnology research at top universities, funded by Amgen",
                application_url="https://amgenscholars.com/",
                application_tips="Highly competitive; strong interest in biotech and bench research",
                housing_provided=True, travel_covered=True,
                category="Corporate", competitiveness="Very High",
                skills_match=["Research"],
            ),
            ResearchOpportunity(
                name="HHMI Janelia Undergraduate Scholars",
                organization="Howard Hughes Medical Institute",
                research_area="Neuroscience, Imaging, Computational Biology",
                location="Janelia Research Campus, Ashburn VA",
                compensation_type="Stipend", stipend_amount=7500,
                duration="Summer 10 weeks", deadline="February 15, 2026",
                gpa_min=3.3, gpa_preferred=3.6,
                eligible_years=["Sophomore", "Junior"],
                majors=["Biology", "Neuroscience", "Physics", "Computer Science", "Engineering"],
                description="Research at HHMI's flagship neuroscience institute",
                application_url="https://www.janelia.org/you-janelia/undergraduate-scholars",
                application_tips="Interdisciplinary projects favored; show quantitative/computational skills",
                housing_provided=True, travel_covered=True,
                category="Corporate", competitiveness="Very High",
                skills_match=["Programming", "Research"],
            ),
        ])

    def add_tech_company_research(self):
        self.opportunities.extend([
            ResearchOpportunity(
                name="Google Research Internship",
                organization="Google",
                research_area="Machine Learning, NLP, Computer Vision, Systems",
                location="Mountain View, NYC, Seattle",
                compensation_type="Paid", stipend_amount=10000,
                duration="Summer 12 weeks", deadline="January 15, 2026",
                gpa_min=3.5, gpa_preferred=3.8,
                eligible_years=["Junior", "Senior"],
                majors=["Computer Science", "Computer Engineering"],
                description="Work alongside Google researchers on publishable research",
                application_url="https://research.google/careers/",
                application_tips="PhD-track students preferred, publications/research experience valued",
                housing_provided=False, travel_covered=False,
                category="Corporate", competitiveness="Very High",
                skills_match=["Programming", "Research"],
            ),
            ResearchOpportunity(
                name="Microsoft Research Internship",
                organization="Microsoft",
                research_area="AI, Programming Languages, HCI, Security, Theory",
                location="Redmond WA, Cambridge MA, NYC",
                compensation_type="Paid", stipend_amount=10000,
                duration="Summer 12 weeks", deadline="January 31, 2026",
                gpa_min=3.5, gpa_preferred=3.8,
                eligible_years=["Junior", "Senior"],
                majors=["Computer Science", "Computer Engineering"],
                description="Research internship at Microsoft Research labs",
                application_url="https://www.microsoft.com/en-us/research/academic-program/",
                application_tips="Top-tier program, research experience and publications highly valued",
                housing_provided=False, travel_covered=False,
                category="Corporate", competitiveness="Very High",
                skills_match=["Programming", "Research"],
            ),
            ResearchOpportunity(
                name="Meta Research Internship",
                organization="Meta",
                research_area="AI, AR/VR, Computer Vision, Systems",
                location="Menlo Park CA, Seattle, NYC",
                compensation_type="Paid", stipend_amount=11000,
                duration="Summer 12-16 weeks", deadline="Rolling (apply by January)",
                gpa_min=3.5, gpa_preferred=3.8,
                eligible_years=["Junior", "Senior"],
                majors=["Computer Science", "Computer Engineering", "Electrical Engineering"],
                description="Research internships across FAIR and Reality Labs",
                application_url="https://www.metacareers.com/careers/research-scientist-internships/",
                application_tips="Tailor application to specific Meta research org",
                housing_provided=False, travel_covered=False,
                category="Corporate", competitiveness="Very High",
                skills_match=["Programming", "Research"],
            ),
            ResearchOpportunity(
                name="NVIDIA Research Internship",
                organization="NVIDIA",
                research_area="GPU Computing, Deep Learning, Graphics, Robotics",
                location="Santa Clara CA, Redmond WA, others",
                compensation_type="Paid", stipend_amount=10500,
                duration="Summer 12 weeks", deadline="February 1, 2026",
                gpa_min=3.4, gpa_preferred=3.7,
                eligible_years=["Junior", "Senior"],
                majors=["Computer Science", "Computer Engineering", "Electrical Engineering"],
                description="Research at NVIDIA on the future of computing and AI",
                application_url="https://www.nvidia.com/en-us/about-nvidia/careers/",
                application_tips="CUDA / parallel programming experience valued; ML coursework expected",
                housing_provided=False, travel_covered=False,
                category="Corporate", competitiveness="Very High",
                skills_match=["Programming", "Research"],
            ),
        ])

    def add_international_programs(self):
        self.opportunities.extend([
            ResearchOpportunity(
                name="DAAD RISE (Research Internships in Science and Engineering)",
                organization="DAAD (German Academic Exchange Service)",
                research_area="STEM",
                location="Germany (host research labs)",
                compensation_type="Stipend", stipend_amount=2800,
                duration="Summer 10-12 weeks", deadline="December 15, 2025",
                gpa_min=3.0, gpa_preferred=3.4,
                eligible_years=["Sophomore", "Junior", "Senior"],
                majors=["Engineering", "Computer Science", "Biology", "Chemistry", "Physics", "Mathematics"],
                description="Research with German universities/labs; living + travel stipend",
                application_url="https://www.daad.de/rise/en/",
                application_tips="Apply early; project-based matching with German faculty",
                housing_provided=False, travel_covered=True,
                category="International", competitiveness="Medium",
                skills_match=["Research"],
            ),
            ResearchOpportunity(
                name="CERN Summer Student Programme",
                organization="CERN",
                research_area="Particle Physics, Computing, Engineering",
                location="Geneva, Switzerland",
                compensation_type="Stipend", stipend_amount=5500,
                duration="Summer 8-13 weeks", deadline="January 26, 2026",
                gpa_min=3.3, gpa_preferred=3.6,
                eligible_years=["Junior", "Senior"],
                majors=["Physics", "Computer Science", "Mathematics", "Engineering"],
                description="Work at the world's largest particle physics lab",
                application_url="https://careers.cern/summer",
                application_tips="Open to US students through US-CERN program; strong physics background",
                housing_provided=True, travel_covered=True,
                category="International", competitiveness="Very High",
                skills_match=["Programming", "Research"],
            ),
            ResearchOpportunity(
                name="Mitacs Globalink Research Internship",
                organization="Mitacs (Canada)",
                research_area="STEM, Social Sciences, Humanities",
                location="Canadian universities",
                compensation_type="Stipend + Travel", stipend_amount=4500,
                duration="Summer 12 weeks", deadline="September 18, 2025 (annual)",
                gpa_min=3.0, gpa_preferred=3.5,
                eligible_years=["Sophomore", "Junior"],
                majors=["All majors"],
                description="Faculty-mentored research at Canadian universities",
                application_url="https://www.mitacs.ca/en/programs/globalink/globalink-research-internship",
                application_tips="Available to US, international students; pick projects matching skills",
                housing_provided=True, travel_covered=True,
                category="International", competitiveness="Medium",
                skills_match=["Research"],
            ),
        ])

    def add_research_opportunity(self, opportunity: ResearchOpportunity):
        self.opportunities.append(opportunity)

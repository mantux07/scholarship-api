#!/usr/bin/env python3
"""
Scholarship Database Loader
Loads scholarships from JSON database instead of hardcoded values
"""

import json
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path


class ScholarshipDatabase:
    """Load and manage scholarship database from JSON"""

    def __init__(self, json_file: str = "scholarship_database.json"):
        self.json_file = json_file
        self.data = self.load_database()

    def load_database(self) -> Dict:
        """Load scholarship database from JSON file"""
        try:
            json_path = Path(self.json_file)
            if not json_path.exists():
                print(f"⚠️  Warning: {self.json_file} not found. Using empty database.")
                return {"scholarships": [], "metadata": {}}

            with open(json_path, 'r') as f:
                return json.load(f)

        except json.JSONDecodeError as e:
            print(f"❌ Error parsing JSON: {e}")
            return {"scholarships": [], "metadata": {}}
        except Exception as e:
            print(f"❌ Error loading database: {e}")
            return {"scholarships": [], "metadata": {}}

    def get_all_scholarships(self) -> List[Dict]:
        """Get all scholarships"""
        return self.data.get("scholarships", [])

    def get_active_scholarships(self) -> List[Dict]:
        """Get only active scholarships"""
        return [s for s in self.get_all_scholarships() if s.get("status") == "active"]

    def get_scholarships_by_category(self, category: str) -> List[Dict]:
        """Get scholarships by category"""
        return [s for s in self.get_active_scholarships() if s.get("category") == category]

    def get_scholarships_for_profile(self, profile: Dict) -> List[Dict]:
        """
        Filter scholarships based on student profile

        Args:
            profile: Dict with keys like gpa, major, heritage, university, etc.

        Returns:
            List of matching scholarships
        """
        scholarships = self.get_active_scholarships()
        matched = []

        for scholarship in scholarships:
            if self.matches_profile(scholarship, profile):
                matched.append(scholarship)

        return matched

    def matches_profile(self, scholarship: Dict, profile: Dict) -> bool:
        """
        Check if scholarship matches student profile

        Args:
            scholarship: Scholarship dict from database
            profile: Student profile dict

        Returns:
            True if student qualifies, False otherwise
        """
        requirements = scholarship.get("requirements", {})

        # Check GPA
        student_gpa = profile.get("gpa", 0)
        min_gpa = scholarship.get("gpa_min", 0)
        if student_gpa < min_gpa:
            return False

        # Check major
        if "major" in requirements:
            student_major = profile.get("major", "").lower()
            required_majors = [m.lower() for m in requirements["major"]]
            if not any(maj in student_major for maj in required_majors):
                return False

        # Check heritage/ethnicity
        if "heritage" in requirements:
            student_heritage = profile.get("heritage", "").lower()
            required_heritages = [h.lower() for h in requirements["heritage"]]
            if not any(her in student_heritage for her in required_heritages):
                return False

        # Check university
        if "university" in requirements:
            student_university = profile.get("university", "").lower()
            required_universities = [u.lower() for u in requirements["university"]]
            if not any(uni in student_university for uni in required_universities):
                return False

        # Check gender
        if "gender" in requirements:
            student_gender = profile.get("gender", "").lower()
            required_genders = [g.lower() for g in requirements["gender"]]
            if not any(gen in student_gender for gen in required_genders):
                return False

        # Check clubs/organizations
        if "clubs" in requirements:
            student_clubs = profile.get("clubs", "").lower()
            required_clubs = [c.lower() for c in requirements["clubs"]]
            if not any(club in student_clubs for club in required_clubs):
                return False

        # Check citizenship/residency
        if "citizenship" in requirements:
            student_residency = profile.get("residency", "").lower()
            if student_residency == "international":
                return False  # International students can't apply

        # Check year in school
        if "year" in requirements:
            student_year = profile.get("year", "").lower()
            required_years = [y.lower() for y in requirements["year"]]
            # Use exact matching to avoid "Senior" matching "High School Senior"
            if not any(student_year == year for year in required_years):
                return False

        # Check state (geographic requirement)
        if "state" in requirements:
            student_state = profile.get("state", "").lower()
            required_states = [s.lower() for s in requirements["state"]]
            # Check if student's state matches any required state
            if not any(req_state.lower() in student_state or student_state in req_state.lower() for req_state in requirements["state"]):
                return False

        # Check residency status (e.g., Undocumented, DACA, TPS)
        if "residency" in requirements:
            student_residency = profile.get("residency", "").lower()
            required_residency = [r.lower() for r in requirements["residency"]]
            # Must match one of the residency statuses
            if not any(req in student_residency for req in required_residency):
                return False

        return True

    def get_scholarship_by_id(self, scholarship_id: str) -> Optional[Dict]:
        """Get a specific scholarship by ID"""
        for scholarship in self.get_all_scholarships():
            if scholarship.get("id") == scholarship_id:
                return scholarship
        return None

    def update_scholarship(self, scholarship_id: str, updates: Dict) -> bool:
        """
        Update a scholarship in the database

        Args:
            scholarship_id: ID of scholarship to update
            updates: Dict of fields to update

        Returns:
            True if updated, False if not found
        """
        for scholarship in self.data["scholarships"]:
            if scholarship["id"] == scholarship_id:
                scholarship.update(updates)
                scholarship["last_verified"] = datetime.now().strftime("%Y-%m-%d")
                return True
        return False

    def save_database(self) -> bool:
        """
        Save database back to JSON file

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            self.data["last_updated"] = datetime.now().strftime("%Y-%m-%d")

            # Update metadata
            scholarships = self.data.get("scholarships", [])
            self.data["metadata"]["total_scholarships"] = len(scholarships)

            with open(self.json_file, 'w') as f:
                json.dump(self.data, f, indent=2)

            print(f"✅ Database saved to {self.json_file}")
            return True

        except Exception as e:
            print(f"❌ Error saving database: {e}")
            return False

    def get_database_info(self) -> Dict:
        """Get database metadata"""
        return {
            "version": self.data.get("version", "Unknown"),
            "last_updated": self.data.get("last_updated", "Unknown"),
            "total_scholarships": len(self.get_all_scholarships()),
            "active_scholarships": len(self.get_active_scholarships()),
            "categories": self.data.get("metadata", {}).get("categories", [])
        }


# Test/example usage
if __name__ == "__main__":
    print("=" * 60)
    print("Scholarship Database Loader - Test")
    print("=" * 60)
    print()

    # Load database
    db = ScholarshipDatabase()
    info = db.get_database_info()

    print(f"Database Version: {info['version']}")
    print(f"Last Updated: {info['last_updated']}")
    print(f"Total Scholarships: {info['total_scholarships']}")
    print(f"Active Scholarships: {info['active_scholarships']}")
    print()

    # Test profile matching
    test_profile = {
        "gpa": 3.5,
        "major": "Engineering",
        "heritage": "Black",
        "university": "Purdue University",
        "residency": "In-State",
        "gender": "Male",
        "clubs": "NSBE"
    }

    print("Test Profile:")
    for key, value in test_profile.items():
        print(f"  {key}: {value}")
    print()

    matches = db.get_scholarships_for_profile(test_profile)
    print(f"Matching Scholarships: {len(matches)}")
    for s in matches:
        print(f"  ✓ {s['name']} - {s['amount_display']}")
    print()

    print("=" * 60)

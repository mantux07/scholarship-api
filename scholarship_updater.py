#!/usr/bin/env python3
"""
Weekly Scholarship Updater
Automatically updates scholarship database from official sources
"""

import json
import requests
import time
from datetime import datetime
from typing import Dict, List, Optional
from bs4 import BeautifulSoup
from scholarship_database_loader import ScholarshipDatabase


class ScholarshipUpdater:
    """Update scholarship database from web sources"""

    def __init__(self, db_file: str = "scholarship_database.json"):
        self.db = ScholarshipDatabase(db_file)
        self.changes = []
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Scholarship System Auto-Updater/1.0)'
        }

    def run_update(self) -> List[Dict]:
        """
        Run weekly update process

        Returns:
            List of changes made
        """
        print("=" * 70)
        print("SCHOLARSHIP DATABASE UPDATE")
        print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)
        print()

        # Update existing scholarships
        print("📋 UPDATING EXISTING SCHOLARSHIPS")
        print("-" * 70)
        self.update_nsbe()
        time.sleep(3)  # Be polite to servers

        self.update_shpe()
        time.sleep(3)

        self.update_swe()
        time.sleep(3)

        # Add more updaters as needed
        # self.update_purdue()
        # self.update_coca_cola()

        print()
        print("🔍 DISCOVERING NEW SCHOLARSHIPS")
        print("-" * 70)

        # Discover new scholarships from various sources
        new_scholarships = self.discover_new_scholarships()

        if new_scholarships:
            print(f"\n✨ Discovered {len(new_scholarships)} new scholarship(s)!")
            for s in new_scholarships:
                print(f"  • {s['name']} - {s['amount_display']}")

        # Save changes if any
        if self.changes or new_scholarships:
            print(f"\n✅ Found {len(self.changes)} updates and {len(new_scholarships)} new scholarships")
            for change in self.changes:
                print(f"  • {change['scholarship']}: {change['field']} "
                      f"changed from '{change['old']}' to '{change['new']}'")

            self.db.save_database()
            print("\n✅ Database updated successfully!")
        else:
            print("\n✅ No changes detected. Database is current.")

        print("\n" + "=" * 70)
        return self.changes

    def update_nsbe(self):
        """Update NSBE scholarship information"""
        print("📡 Updating NSBE Scholarship...")

        try:
            # Note: This is a template - actual scraping logic depends on website structure
            url = "https://www.nsbe.org/scholarships"

            # For now, we'll do basic checks
            # In production, you'd scrape the actual page
            response = requests.get(url, headers=self.headers, timeout=10)

            if response.status_code == 200:
                # Parse the page (simplified example)
                # soup = BeautifulSoup(response.content, 'html.parser')

                # For demonstration, let's just verify the page exists
                updates = {
                    "last_verified": datetime.now().strftime("%Y-%m-%d"),
                    "status": "active"
                }

                # Check if deadline info is on the page
                if "march" in response.text.lower() and "2026" in response.text:
                    updates["deadline"] = "March 15, 2026"

                # Update database
                self._update_scholarship("nsbe-001", updates)
                print("  ✅ NSBE verified and updated")
            else:
                print(f"  ⚠️  Could not reach NSBE website (HTTP {response.status_code})")

        except requests.exceptions.Timeout:
            print("  ⚠️  Timeout connecting to NSBE website")
        except Exception as e:
            print(f"  ❌ Error updating NSBE: {e}")

    def update_shpe(self):
        """Update SHPE scholarship information"""
        print("📡 Updating SHPE Scholarship...")

        try:
            url = "https://www.shpe.org/scholarships"
            response = requests.get(url, headers=self.headers, timeout=10)

            if response.status_code == 200:
                updates = {
                    "last_verified": datetime.now().strftime("%Y-%m-%d"),
                    "status": "active"
                }

                # Check for deadline mentions
                if "april" in response.text.lower() and "2026" in response.text:
                    updates["deadline"] = "April 1, 2026"

                self._update_scholarship("shpe-001", updates)
                print("  ✅ SHPE verified and updated")
            else:
                print(f"  ⚠️  Could not reach SHPE website (HTTP {response.status_code})")

        except Exception as e:
            print(f"  ❌ Error updating SHPE: {e}")

    def update_swe(self):
        """Update SWE scholarship information"""
        print("📡 Updating SWE Scholarship...")

        try:
            url = "https://swe.org/scholarships"
            response = requests.get(url, headers=self.headers, timeout=10)

            if response.status_code == 200:
                updates = {
                    "last_verified": datetime.now().strftime("%Y-%m-%d"),
                    "status": "active"
                }

                # Check for deadline mentions
                if "february" in response.text.lower() and "2026" in response.text:
                    updates["deadline"] = "February 15, 2026"

                self._update_scholarship("swe-001", updates)
                print("  ✅ SWE verified and updated")
            else:
                print(f"  ⚠️  Could not reach SWE website (HTTP {response.status_code})")

        except Exception as e:
            print(f"  ❌ Error updating SWE: {e}")

    def _update_scholarship(self, scholarship_id: str, updates: Dict):
        """
        Update a scholarship and track changes

        Args:
            scholarship_id: ID of scholarship to update
            updates: Dict of fields to update
        """
        scholarship = self.db.get_scholarship_by_id(scholarship_id)
        if not scholarship:
            print(f"  ⚠️  Scholarship {scholarship_id} not found in database")
            return

        # Track what changed
        for key, new_value in updates.items():
            old_value = scholarship.get(key)
            if old_value != new_value and key != "last_verified":
                self.changes.append({
                    "scholarship": scholarship["name"],
                    "field": key,
                    "old": old_value,
                    "new": new_value,
                    "timestamp": datetime.now().isoformat()
                })

        # Apply updates
        self.db.update_scholarship(scholarship_id, updates)

    def update_deadline_years(self):
        """
        Update deadline years to next year if deadline has passed

        Example: If "March 15, 2025" has passed, update to "March 15, 2026"
        """
        print("📅 Checking for expired deadlines to roll over...")

        today = datetime.now()
        scholarships = self.db.get_all_scholarships()
        rolled_over = 0

        for scholarship in scholarships:
            deadline_str = scholarship.get("deadline", "")

            # Skip rolling/varies deadlines
            if deadline_str.lower() in ["rolling", "varies", "ongoing"]:
                continue

            # Try to parse deadline
            try:
                # Common formats
                for fmt in ["%B %d, %Y", "%b %d, %Y", "%m/%d/%Y"]:
                    try:
                        deadline_date = datetime.strptime(deadline_str, fmt)

                        # If deadline has passed, roll to next year
                        if deadline_date < today:
                            new_deadline_date = deadline_date.replace(year=deadline_date.year + 1)
                            new_deadline_str = new_deadline_date.strftime(fmt)

                            self._update_scholarship(scholarship["id"], {
                                "deadline": new_deadline_str
                            })

                            rolled_over += 1
                            print(f"  📅 Rolled over: {scholarship['name']} → {new_deadline_str}")
                        break

                    except ValueError:
                        continue

            except Exception as e:
                continue

        if rolled_over > 0:
            print(f"\n✅ Rolled over {rolled_over} deadline(s) to next year")
        else:
            print("  ✅ No deadlines needed rolling over")

    def discover_new_scholarships(self) -> List[Dict]:
        """
        Discover new scholarships from various sources

        Returns:
            List of newly discovered scholarships
        """
        new_scholarships = []

        # Method 1: Check organization directories
        new_scholarships.extend(self.discover_from_organization_directories())

        # Method 2: Check university scholarship pages
        # new_scholarships.extend(self.discover_from_university_pages())

        # Method 3: Check government databases
        # new_scholarships.extend(self.discover_from_government_sources())

        return new_scholarships

    def discover_from_organization_directories(self) -> List[Dict]:
        """
        Discover scholarships from professional organization directories

        Sources to check:
        - STEM organizations (IEEE, ACM, ASME, etc.)
        - Diversity organizations (NSBE, SHPE, SWE, AISES, etc.)
        - Industry associations
        """
        print("  🔍 Checking professional organization directories...")

        # Example: Check for other engineering societies
        # In production, this would scrape organization websites

        discovered = []

        # Template for discovered scholarships
        # This would be populated from actual web scraping
        scholarship_leads = [
            {
                "org": "ASME",
                "url": "https://www.asme.org/career-education/scholarships-and-grants",
                "estimated_amount": "$1,000-$10,000"
            },
            {
                "org": "IEEE",
                "url": "https://www.ieee.org/membership/students/scholarships",
                "estimated_amount": "$10,000"
            },
            {
                "org": "AISES",
                "url": "https://www.aises.org/scholarships",
                "estimated_amount": "$1,000-$5,000"
            }
        ]

        # Check each lead (simplified - in production would scrape details)
        for lead in scholarship_leads:
            try:
                response = requests.get(lead["url"], headers=self.headers, timeout=10)
                if response.status_code == 200 and "scholarship" in response.text.lower():
                    print(f"    ✅ Found scholarships at {lead['org']}")
                    # In production: scrape and parse scholarship details
                    # For now, log that we found it
                else:
                    print(f"    ⚠️  No scholarships found at {lead['org']}")
            except Exception as e:
                print(f"    ❌ Error checking {lead['org']}: {e}")

        return discovered

    def discover_from_university_pages(self) -> List[Dict]:
        """
        Discover scholarships from university financial aid pages

        Top universities to check:
        - MIT, Stanford, Caltech (tech schools)
        - Purdue, Georgia Tech, UIUC (engineering)
        - Ivy League schools
        """
        print("  🔍 Checking university scholarship pages...")

        discovered = []
        # Implementation would go here

        return discovered

    def discover_from_government_sources(self) -> List[Dict]:
        """
        Discover scholarships from government databases

        Sources:
        - Federal Student Aid
        - Department of Education
        - State education departments
        """
        print("  🔍 Checking government scholarship databases...")

        discovered = []
        # Implementation would go here

        return discovered

    def add_new_scholarship_to_database(self, scholarship_data: Dict) -> bool:
        """
        Add a newly discovered scholarship to the database

        Args:
            scholarship_data: Dict containing scholarship information

        Returns:
            True if added successfully
        """
        # Generate unique ID
        scholarship_id = f"{scholarship_data['name'].lower().replace(' ', '-')}-001"

        # Check if already exists
        existing = self.db.get_scholarship_by_id(scholarship_id)
        if existing:
            print(f"  ⚠️  Scholarship {scholarship_id} already exists")
            return False

        # Add to database
        self.db.data["scholarships"].append(scholarship_data)

        self.changes.append({
            "scholarship": scholarship_data["name"],
            "field": "NEW",
            "old": None,
            "new": "Added to database",
            "timestamp": datetime.now().isoformat()
        })

        return True

    def generate_update_report(self) -> str:
        """Generate a summary report of changes"""
        if not self.changes:
            return "No changes were made to the scholarship database."

        report = f"Scholarship Database Update Report\n"
        report += f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        report += f"\n{len(self.changes)} changes made:\n\n"

        for change in self.changes:
            report += f"• {change['scholarship']}\n"
            report += f"  Field: {change['field']}\n"
            report += f"  Old: {change['old']}\n"
            report += f"  New: {change['new']}\n\n"

        return report


def main():
    """Main entry point for the updater"""
    updater = ScholarshipUpdater()

    # Run the update
    changes = updater.run_update()

    # Check for deadline rollovers
    print()
    updater.update_deadline_years()

    # Generate report
    if changes:
        report = updater.generate_update_report()
        print("\n" + "=" * 70)
        print("UPDATE REPORT")
        print("=" * 70)
        print(report)

        # Save report to file
        report_file = f"update_report_{datetime.now().strftime('%Y%m%d')}.txt"
        with open(report_file, 'w') as f:
            f.write(report)
        print(f"📝 Report saved to {report_file}")


if __name__ == "__main__":
    main()

import unittest

from engine import analyze_application, generate_package


PROFILE = {
    "name": "Alex Morgan",
    "headline": "Product and commercial systems builder",
    "summary": "Cross-functional operator.",
    "skills": ["product marketing", "CRM", "automation"],
    "experiences": [
        {
            "company": "Example Co.",
            "title": "Principal",
            "dates": "2020–Present",
            "bullets": [
                "Built go-to-market systems and CRM workflows.",
                "Led customer discovery and competitive analysis.",
            ],
        }
    ],
}


class EngineTests(unittest.TestCase):
    def test_narrative_material_is_candidate_not_approved(self):
        result = analyze_application(
            PROFILE,
            "I consolidated seven automation workflows and improved follow-up consistency.",
            "We need product marketing, automation, and stakeholder leadership.",
        )
        self.assertTrue(result["candidate_evidence"])
        self.assertEqual(result["candidate_evidence"][0]["status"], "CANDIDATE")
        self.assertNotIn("consolidated seven automation workflows and improved follow-up consistency.", [item["claim"] for item in result["approved_matches"]])

    def test_application_only_decision_is_included_in_package(self):
        analysis = analyze_application(
            PROFILE,
            "I built a launch operating model for a new product marketing motion.",
            "We need product marketing and go-to-market leadership.",
        )
        card_id = analysis["candidate_evidence"][0]["id"]
        package = generate_package(PROFILE, "", "We need product marketing.", analysis, {card_id: "application_only"})
        self.assertIn("launch operating model", package["resume"])
        self.assertEqual(package["review_ledger"][0]["decision"], "application_only")

    def test_rejected_candidate_is_not_included(self):
        analysis = analyze_application(
            PROFILE,
            "I built a launch operating model for a new product marketing motion.",
            "We need product marketing and go-to-market leadership.",
        )
        card_id = analysis["candidate_evidence"][0]["id"]
        package = generate_package(PROFILE, "", "We need product marketing.", analysis, {card_id: "reject"})
        self.assertNotIn("launch operating model", package["resume"])


if __name__ == "__main__":
    unittest.main()

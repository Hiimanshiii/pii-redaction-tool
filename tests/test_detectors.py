import unittest
from src.detectors import PIIDetector, DetectedEntity

class TestPIIDetector(unittest.TestCase):
    def setUp(self):
        self.detector = PIIDetector()

    def test_valid_email(self):
        text = "Contact us at support@example.com for help."
        results = self.detector.detect(text)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].entity_type, "EMAIL")
        self.assertEqual(results[0].text, "support@example.com")

    def test_indian_mobile_with_prefix(self):
        formats = [
            "My number is +91 9876543210.",
            "Contact: +91 98765 43210",
            "Call +91-9876543210 now",
            "Send text to 91 9876543210"
        ]
        for text in formats:
            with self.subTest(text=text):
                results = self.detector.detect(text)
                self.assertEqual(len(results), 1)
                self.assertEqual(results[0].entity_type, "PHONE")
                self.assertTrue("98765" in results[0].text)

    def test_indian_mobile_without_country_code(self):
        text = "Direct call to 9876543210 is possible."
        results = self.detector.detect(text)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].entity_type, "PHONE")
        self.assertEqual(results[0].text, "9876543210")

    def test_indian_landline_with_prefix(self):
        formats = [
            "Call +91 22 4009 4400 inside Mumbai.",
            "Reach us at +91 20 45053237."
        ]
        expected_texts = [
            "+91 22 4009 4400",
            "+91 20 45053237"
        ]
        for text, expected in zip(formats, expected_texts):
            with self.subTest(text=text):
                results = self.detector.detect(text)
                self.assertEqual(len(results), 1)
                self.assertEqual(results[0].entity_type, "PHONE")
                self.assertEqual(results[0].text, expected)

    def test_valid_ipv4(self):
        text = "Server IP is 192.168.1.1."
        results = self.detector.detect(text)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].entity_type, "IP_ADDRESS")
        self.assertEqual(results[0].text, "192.168.1.1")

    def test_invalid_ipv4(self):
        text = "Invalid IP: 999.999.999.999 or 256.100.50.0"
        results = self.detector.detect(text)
        self.assertEqual(len(results), 0)

    def test_valid_ssn(self):
        text = "SSN format is 123-45-6789."
        results = self.detector.detect(text)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].entity_type, "SSN")
        self.assertEqual(results[0].text, "123-45-6789")

    def test_invalid_ssn(self):
        invalid_texts = [
            "SSN is 000-12-3456",
            "SSN is 666-12-3456",
            "SSN is 901-12-3456",
            "SSN is 123-00-6789",
            "SSN is 123-45-0000"
        ]
        for text in invalid_texts:
            with self.subTest(text=text):
                results = self.detector.detect(text)
                self.assertEqual(len(results), 0)

    def test_valid_credit_card(self):
        text = "Payment card 4111 1111 1111 1111 used."
        results = self.detector.detect(text)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].entity_type, "CREDIT_CARD")
        self.assertEqual(results[0].text, "4111 1111 1111 1111")

    def test_invalid_credit_card(self):
        text = "Bad card 4111 1111 1111 1112 used."
        results = self.detector.detect(text)
        self.assertEqual(len(results), 0)

    def test_no_false_positives(self):
        false_positive_cases = [
            "Section 32",
            "December 10, 2025",
            "₹4,200.00 million",
            "U28129PN1979PLC141032"
        ]
        for text in false_positive_cases:
            with self.subTest(text=text):
                results = self.detector.detect(text)
                # Ensure no structured PII gets matched.
                # If named entity detection finds "December" as DATE, it is ignored anyway.
                # If "U28129PN1979PLC141032" is found as ORG by spaCy, we check results.
                # However, for structured tests, none should match.
                # Let's filter to check that no PHONE, EMAIL, IP_ADDRESS, SSN, or CREDIT_CARD matches.
                structured_matches = [r for r in results if r.entity_type not in ("PERSON", "COMPANY")]
                self.assertEqual(len(structured_matches), 0)

    def test_person_detection(self):
        text = "The company was founded by Sarthak Malvadkar in 2020."
        results = self.detector.detect(text)
        person_matches = [r for r in results if r.entity_type == "PERSON"]
        self.assertEqual(len(person_matches), 1)
        self.assertEqual(person_matches[0].text, "Sarthak Malvadkar")

    def test_person_filtering_tuned(self):
        # "Offer" and "Directors" (single-word, headings/uppercase) must be rejected
        text_offer = "This is a public Offer for Directors."
        results = self.detector.detect(text_offer)
        person_matches = [r for r in results if r.entity_type == "PERSON"]
        self.assertEqual(len(person_matches), 0)

        # "ISO 9001:2015" (contains digits and colon) must be rejected
        text_iso = "Certified under ISO 9001:2015 standards."
        results_iso = self.detector.detect(text_iso)
        person_matches_iso = [r for r in results_iso if r.entity_type == "PERSON"]
        self.assertEqual(len(person_matches_iso), 0)

    def test_company_suffix_detection_complete(self):
        text = "We are reviewing KSH International Limited today."
        results = self.detector.detect(text)
        company_matches = [r for r in results if r.entity_type == "COMPANY"]
        self.assertEqual(len(company_matches), 1)
        self.assertEqual(company_matches[0].text, "KSH International Limited")
        self.assertGreaterEqual(company_matches[0].confidence, 0.90)

    def test_min_confidence_filter(self):
        text = "Let's review Montreal Business Centre (which gets spaCy ORG 0.80) and HDFC Bank (suffix ORG 0.90)."
        
        # Without filter (min_confidence=0.0)
        all_results = self.detector.detect(text, min_confidence=0.0)
        companies_all = [r for r in all_results if r.entity_type == "COMPANY"]
        
        # With filter (min_confidence=0.85)
        filtered_results = self.detector.detect(text, min_confidence=0.85)
        companies_filtered = [r for r in filtered_results if r.entity_type == "COMPANY"]
        
        # Suffix COMPANY (0.90) must remain, but spaCy ORG (0.80) must be filtered out
        for c in companies_filtered:
            self.assertGreaterEqual(c.confidence, 0.85)
            
        # Verify that companies list has HDFC Bank
        hdfc_present_filtered = any("HDFC Bank" in c.text for c in companies_filtered)
        self.assertTrue(hdfc_present_filtered)

    def test_precision_tuning_person(self):
        # Exclusions for PERSON (e.g. "Selling Shareholder")
        results = self.detector.detect("The Selling Shareholder will offer shares.")
        person_matches = [r for r in results if r.entity_type == "PERSON"]
        self.assertEqual(len(person_matches), 0)

        # Location signals (e.g. "Bandra Complex", "Taluka Khed")
        results_loc = self.detector.detect("He lives in Bandra Complex or Taluka Khed.")
        person_matches_loc = [r for r in results_loc if r.entity_type == "PERSON"]
        self.assertEqual(len(person_matches_loc), 0)

        # Trailing suffix stripping: "Sharmila Joshi Website" -> "Sharmila Joshi"
        text = "Please contact Sharmila Joshi Website for details."
        results_strip = self.detector.detect(text)
        person_matches_strip = [r for r in results_strip if r.entity_type == "PERSON"]
        self.assertEqual(len(person_matches_strip), 1)
        self.assertEqual(person_matches_strip[0].text, "Sharmila Joshi")

        # "Soni Website" -> stripped to "Soni" (1 word) -> rejected
        text_rejected = "Contact Soni Website today."
        results_rejected = self.detector.detect(text_rejected)
        person_matches_rejected = [r for r in results_rejected if r.entity_type == "PERSON"]
        self.assertEqual(len(person_matches_rejected), 0)

    def test_precision_tuning_company(self):
        # Exclusions for COMPANY (e.g. "Proposed Capital", "Indian Securities")
        results = self.detector.detect("Proposed Capital is required under Indian Securities.")
        company_matches = [r for r in results if r.entity_type == "COMPANY"]
        self.assertEqual(len(company_matches), 0)

    def test_new_contextual_detectors(self):
        # ADDRESS positive
        addr_pos = "Office No. 201, Tower 2, World Trade Center, Kharadi, Pune, Maharashtra 411014"
        res_addr_pos = self.detector.detect(addr_pos)
        addr_matches_pos = [r for r in res_addr_pos if r.entity_type == "ADDRESS"]
        self.assertEqual(len(addr_matches_pos), 1)
        self.assertEqual(addr_matches_pos[0].text, addr_pos)
        self.assertEqual(addr_matches_pos[0].confidence, 0.90)

        # ADDRESS negative
        addr_neg = "The company operates in Pune and Maharashtra."
        res_addr_neg = self.detector.detect(addr_neg)
        addr_matches_neg = [r for r in res_addr_neg if r.entity_type == "ADDRESS"]
        self.assertEqual(len(addr_matches_neg), 0)

        # DOB positives
        dob_pos_1 = "Date of Birth: 15/08/1985"
        res_dob_pos_1 = self.detector.detect(dob_pos_1)
        dob_matches_pos_1 = [r for r in res_dob_pos_1 if r.entity_type == "DATE_OF_BIRTH"]
        self.assertEqual(len(dob_matches_pos_1), 1)
        self.assertEqual(dob_matches_pos_1[0].text, "15/08/1985")
        self.assertEqual(dob_matches_pos_1[0].confidence, 0.95)

        dob_pos_2 = "DOB: August 15, 1985"
        res_dob_pos_2 = self.detector.detect(dob_pos_2)
        dob_matches_pos_2 = [r for r in res_dob_pos_2 if r.entity_type == "DATE_OF_BIRTH"]
        self.assertEqual(len(dob_matches_pos_2), 1)
        self.assertEqual(dob_matches_pos_2[0].text, "August 15, 1985")
        self.assertEqual(dob_matches_pos_2[0].confidence, 0.95)

        # DOB negatives
        dob_neg_1 = "Dated December 10, 2025"
        res_dob_neg_1 = self.detector.detect(dob_neg_1)
        dob_matches_neg_1 = [r for r in res_dob_neg_1 if r.entity_type == "DATE_OF_BIRTH"]
        self.assertEqual(len(dob_matches_neg_1), 0)

        dob_neg_2 = "Incorporated on January 15, 1979"
        res_dob_neg_2 = self.detector.detect(dob_neg_2)
        dob_matches_neg_2 = [r for r in res_dob_neg_2 if r.entity_type == "DATE_OF_BIRTH"]
        self.assertEqual(len(dob_matches_neg_2), 0)

        # PAN positive
        pan_pos = "My PAN number is ABCDE1234F."
        res_pan_pos = self.detector.detect(pan_pos)
        pan_matches_pos = [r for r in res_pan_pos if r.entity_type == "PAN"]
        self.assertEqual(len(pan_matches_pos), 1)
        self.assertEqual(pan_matches_pos[0].text, "ABCDE1234F")
        self.assertEqual(pan_matches_pos[0].confidence, 0.95)

        # PAN negative (CIN)
        pan_neg = "Our CIN is U28129PN1979PLC141032."
        res_pan_neg = self.detector.detect(pan_neg)
        pan_matches_neg = [r for r in res_pan_neg if r.entity_type == "PAN"]
        self.assertEqual(len(pan_matches_neg), 0)

        # AADHAAR positive (Verhoeff-valid synthetic number)
        aadhaar_pos = "My Aadhaar is 1234 5678 9010."
        res_aadhaar_pos = self.detector.detect(aadhaar_pos)
        aadhaar_matches_pos = [r for r in res_aadhaar_pos if r.entity_type == "AADHAAR"]
        self.assertEqual(len(aadhaar_matches_pos), 1)
        self.assertEqual(aadhaar_matches_pos[0].text, "1234 5678 9010")
        self.assertEqual(aadhaar_matches_pos[0].confidence, 0.90)

        # AADHAAR negative (Verhoeff-invalid)
        aadhaar_neg = "My arbitrary number is 1234 5678 9012."
        res_aadhaar_neg = self.detector.detect(aadhaar_neg)
        aadhaar_matches_neg = [r for r in res_aadhaar_neg if r.entity_type == "AADHAAR"]
        self.assertEqual(len(aadhaar_matches_neg), 0)

    def test_same_span_conflict_prefer_structured(self):
        # Test that PAN/AADHAAR takes preference over PERSON/COMPANY on the same span.
        results = self.detector.detect("My identifier is ABCDE1234F.")
        matches = [r for r in results if r.text == "ABCDE1234F"]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].entity_type, "PAN")

    def test_precision_recall_regressions(self) -> None:
        # 1. ADDRESS regression tests
        text_addr1 = "Registered Office: 11/3, 11/4 and 11/5, Village Birdewadi, Chakan Taluka - Khed, Pune \u2013 410 501, Maharashtra, India;"
        results_addr1 = self.detector.detect(text_addr1)
        addr1_matches = [r for r in results_addr1 if r.entity_type == "ADDRESS"]
        self.assertEqual(len(addr1_matches), 1)
        self.assertEqual(addr1_matches[0].text, "11/3, 11/4 and 11/5, Village Birdewadi, Chakan Taluka - Khed, Pune \u2013 410 501, Maharashtra, India")

        text_addr2 = "1st Floor, L B S Marg, Vikhroli (West) Mumbai 400083, (Maharashtra), India Telephone: +91 81081 14949"
        results_addr2 = self.detector.detect(text_addr2)
        addr2_matches = [r for r in results_addr2 if r.entity_type == "ADDRESS"]
        self.assertEqual(len(addr2_matches), 1)
        self.assertEqual(addr2_matches[0].text, "1st Floor, L B S Marg, Vikhroli (West) Mumbai 400083, (Maharashtra), India")

        # 2. PHONE regression tests
        text_phone1 = "Telephone: + 91 91586 40360"
        results_phone1 = self.detector.detect(text_phone1)
        phone1_matches = [r for r in results_phone1 if r.entity_type == "PHONE"]
        self.assertEqual(len(phone1_matches), 1)
        self.assertEqual(phone1_matches[0].text, "+ 91 91586 40360")

        # 3. COMPANY regression tests
        text_co1 = "KSH INTERNATIONAL LIMITED"
        results_co1 = self.detector.detect(text_co1)
        co1_matches = [r for r in results_co1 if r.entity_type == "COMPANY"]
        self.assertEqual(len(co1_matches), 1)
        self.assertEqual(co1_matches[0].text, "KSH INTERNATIONAL LIMITED")
        self.assertEqual(co1_matches[0].confidence, 0.90)

if __name__ == '__main__':
    unittest.main()

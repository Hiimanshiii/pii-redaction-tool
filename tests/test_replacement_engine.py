import unittest
from src.detectors import DetectedEntity
from src.replacement_engine import ReplacementEngine

class TestReplacementEngine(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = ReplacementEngine(seed=42)

    def test_same_person_produces_same_replacement(self) -> None:
        entity1 = DetectedEntity(text="Sarthak Malvadkar", entity_type="PERSON", start=0, end=17, confidence=0.85)
        entity2 = DetectedEntity(text="Sarthak Malvadkar", entity_type="PERSON", start=10, end=27, confidence=0.85)
        
        rep1 = self.engine.get_replacement(entity1)
        rep2 = self.engine.get_replacement(entity2)
        
        self.assertEqual(rep1, rep2)

    def test_person_matching_is_case_insensitive(self) -> None:
        entity1 = DetectedEntity(text="Sarthak Malvadkar", entity_type="PERSON", start=0, end=17, confidence=0.85)
        entity2 = DetectedEntity(text="sarthak malvadkar", entity_type="PERSON", start=0, end=17, confidence=0.85)
        
        rep1 = self.engine.get_replacement(entity1)
        rep2 = self.engine.get_replacement(entity2)
        
        self.assertEqual(rep1, rep2)

    def test_different_person_values_produce_different_replacements(self) -> None:
        entity1 = DetectedEntity(text="Sarthak Malvadkar", entity_type="PERSON", start=0, end=17, confidence=0.85)
        entity2 = DetectedEntity(text="Kushal Hegde", entity_type="PERSON", start=0, end=12, confidence=0.85)
        
        rep1 = self.engine.get_replacement(entity1)
        rep2 = self.engine.get_replacement(entity2)
        
        self.assertNotEqual(rep1, rep2)

    def test_same_email_different_capitalization_produces_same_replacement(self) -> None:
        entity1 = DetectedEntity(text="Sarthak@Ksh.Co.In", entity_type="EMAIL", start=0, end=17, confidence=1.0)
        entity2 = DetectedEntity(text="sarthak@ksh.co.in", entity_type="EMAIL", start=0, end=17, confidence=1.0)
        
        rep1 = self.engine.get_replacement(entity1)
        rep2 = self.engine.get_replacement(entity2)
        
        self.assertEqual(rep1, rep2)

    def test_phone_formatting_variants_map_consistently(self) -> None:
        # Formatting variants: +91, 91, or spaces/hyphens
        entity1 = DetectedEntity(text="+91 22 4009 4400", entity_type="PHONE", start=0, end=16, confidence=0.9)
        entity2 = DetectedEntity(text="91 22 4009 4400", entity_type="PHONE", start=0, end=15, confidence=0.9)
        entity3 = DetectedEntity(text="22 4009 4400", entity_type="PHONE", start=0, end=12, confidence=0.7)
        
        rep1 = self.engine.get_replacement(entity1)
        rep2 = self.engine.get_replacement(entity2)
        rep3 = self.engine.get_replacement(entity3)
        
        # Strip all prefixes and compare key normalization
        self.assertEqual(rep1, rep2)
        self.assertEqual(rep2, rep3)

    def test_person_and_company_with_identical_text_use_different_mapping_keys(self) -> None:
        entity1 = DetectedEntity(text="KSH International", entity_type="PERSON", start=0, end=17, confidence=0.85)
        entity2 = DetectedEntity(text="KSH International", entity_type="COMPANY", start=0, end=17, confidence=0.80)
        
        rep1 = self.engine.get_replacement(entity1)
        rep2 = self.engine.get_replacement(entity2)
        
        # Because keys include entity_type, they must map to different generated values
        self.assertNotEqual(rep1, rep2)

    def test_generated_email_ends_in_example_com(self) -> None:
        entity = DetectedEntity(text="abc@def.com", entity_type="EMAIL", start=0, end=11, confidence=1.0)
        rep = self.engine.get_replacement(entity)
        self.assertTrue(rep.endswith("@example.com"))

    def test_generated_ip_belongs_to_reserved_documentation_range(self) -> None:
        entity = DetectedEntity(text="192.168.1.1", entity_type="IP_ADDRESS", start=0, end=11, confidence=1.0)
        rep = self.engine.get_replacement(entity)
        
        valid_ranges = ["192.0.2.", "198.51.100.", "203.0.113."]
        self.assertTrue(any(rep.startswith(prefix) for prefix in valid_ranges))

    def test_unknown_entity_type_returns_redacted(self) -> None:
        entity = DetectedEntity(text="secret_data", entity_type="UNKNOWN_PII", start=0, end=11, confidence=1.0)
        rep = self.engine.get_replacement(entity)
        self.assertEqual(rep, "[REDACTED]")

    def test_get_mapping_returns_copy_of_mapping(self) -> None:
        entity = DetectedEntity(text="Kushal Hegde", entity_type="PERSON", start=0, end=12, confidence=0.85)
        rep = self.engine.get_replacement(entity)
        
        mapping = self.engine.get_mapping()
        self.assertIn(("PERSON", "kushal hegde"), mapping)
        self.assertEqual(mapping[("PERSON", "kushal hegde")], rep)

    def test_seed_determinism(self) -> None:
        engine1 = ReplacementEngine(seed=42)
        engine2 = ReplacementEngine(seed=42)

        entity = DetectedEntity(text="Sarthak Malvadkar", entity_type="PERSON", start=0, end=17, confidence=0.85)

        rep1 = engine1.get_replacement(entity)
        rep2 = engine2.get_replacement(entity)

        self.assertEqual(rep1, rep2)

if __name__ == '__main__':
    unittest.main()

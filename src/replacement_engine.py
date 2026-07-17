import re
from typing import Dict, Tuple, Set
# pyrefly: ignore [missing-import]
from faker import Faker
from src.detectors import DetectedEntity, validate_verhoeff

class ReplacementEngine:
    """Generates consistent and deterministic synthetic replacements for detected PII."""

    def __init__(self, seed: int = 42) -> None:
        self.fake = Faker("en_IN")
        self.fake.seed_instance(seed)
        
        # Internal dictionary mapping (entity_type, normalized_value) -> replacement_value
        self._mappings: Dict[Tuple[str, str], str] = {}
        
        # Track used replacements to avoid collisions across different entities
        self._used_replacements: Set[str] = set()

    def _normalize(self, entity_type: str, value: str) -> str:
        """Normalize values based on entity type to ensure consistent matching."""
        val = value.strip()
        # Collapse multiple spaces
        val = re.sub(r'\s+', ' ', val)
        val = val.lower()

        if entity_type == "PHONE":
            # Strip all non-digit characters
            digits = re.sub(r'\D', '', val)
            # Standardize Indian country code prefixes
            if len(digits) > 10 and digits.startswith("91"):
                digits = digits[2:]
            return digits

        return val

    def get_replacement(self, entity: DetectedEntity) -> str:
        """Retrieve an existing replacement or generate a new consistent fake one."""
        try:
            norm_val = self._normalize(entity.entity_type, entity.text)
            key = (entity.entity_type, norm_val)

            if key in self._mappings:
                return self._mappings[key]

            # Generate a unique replacement value
            replacement = self._generate_unique_replacement(entity.entity_type, entity.text)
            self._mappings[key] = replacement
            return replacement
        except Exception as e:
            raise RuntimeError("An unexpected error occurred during replacement generation.") from e

    def _generate_unique_replacement(self, entity_type: str, original_value: str) -> str:
        """Generate a replacement, regenerating on collisions to ensure uniqueness."""
        for _ in range(100):
            candidate = self._generate_by_type(entity_type, original_value)
            if candidate not in self._used_replacements:
                self._used_replacements.add(candidate)
                return candidate
        return self._generate_by_type(entity_type, original_value)

    def _generate_by_type(self, entity_type: str, original_value: str) -> str:
        """Internal helper to dispatch replacement generation by PII type."""
        if entity_type == "PERSON":
            return self.fake.name()

        elif entity_type == "EMAIL":
            return self.fake.user_name() + "@example.com"

        elif entity_type == "PHONE":
            # Generate a 10-digit number starting with 9
            suffix = "".join(str(self.fake.random.randint(0, 9)) for _ in range(9))
            phone_10 = f"9{suffix}"
            # Keep country-code style if present in the original value
            if "+" in original_value or "91" in original_value:
                return f"+91 {phone_10}"
            return phone_10

        elif entity_type == "COMPANY":
            co_name = self.fake.company()
            # Ensure it ends with a standard suffix if not already present
            if not any(co_name.endswith(s) for s in ["Limited", "Private Limited", "Pvt. Ltd.", "Ltd.", "LLP"]):
                co_name += " Private Limited"
            return co_name

        elif entity_type == "ADDRESS":
            return self.fake.address().replace("\n", ", ")

        elif entity_type == "SSN":
            return self._generate_ssn()

        elif entity_type == "CREDIT_CARD":
            return self._generate_credit_card()

        elif entity_type == "DATE_OF_BIRTH":
            return self._generate_date_of_birth(original_value)

        elif entity_type == "IP_ADDRESS":
            # Documentation-only IP addresses from RFC-reserved ranges
            prefix = self.fake.random.choice(["192.0.2", "198.51.100", "203.0.113"])
            host = self.fake.random.randint(1, 254)
            return f"{prefix}.{host}"

        elif entity_type == "PAN":
            letters1 = "".join(self.fake.random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ") for _ in range(5))
            digits = "".join(str(self.fake.random.randint(0, 9)) for _ in range(4))
            letter2 = self.fake.random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
            return f"{letters1}{digits}{letter2}"

        elif entity_type == "AADHAAR":
            return self._generate_aadhaar()

        return "[REDACTED]"

    def _generate_ssn(self) -> str:
        """Generate a synthetic SSN satisfying SSN detector constraints."""
        area = self.fake.random.randint(100, 899)
        while area == 666:
            area = self.fake.random.randint(100, 899)
        group = self.fake.random.randint(10, 99)
        serial = self.fake.random.randint(1000, 9999)
        return f"{area:03d}-{group:02d}-{serial:04d}"

    def _generate_credit_card(self) -> str:
        """Generate a synthetic Luhn-valid credit card number."""
        digits = [4, 1, 1, 1] + [self.fake.random.randint(0, 9) for _ in range(11)]
        for check_digit in range(10):
            candidate = digits + [check_digit]
            checksum = 0
            for i, d in enumerate(reversed(candidate)):
                if i % 2 == 1:
                    d *= 2
                    if d > 9:
                        d -= 9
                checksum += d
            if checksum % 10 == 0:
                card_num = "".join(map(str, candidate))
                return f"{card_num[:4]} {card_num[4:8]} {card_num[8:12]} {card_num[12:]}"
        return "4111 1111 1111 1111"

    def _generate_date_of_birth(self, original_value: str) -> str:
        """Generate a plausible adult DOB matching the format of original_value."""
        dt = self.fake.date_of_birth(minimum_age=18, maximum_age=75)
        if "/" in original_value:
            return dt.strftime("%d/%m/%Y")
        elif "-" in original_value:
            if re.match(r'^\d{4}', original_value):
                return dt.strftime("%Y-%m-%d")
            return dt.strftime("%d-%m-%Y")
        else:
            if re.match(r'^\d', original_value.strip()):
                return dt.strftime("%d %B %Y")
            return dt.strftime("%B %d, %Y")

    def _generate_aadhaar(self) -> str:
        """Generate a synthetic 12-digit Aadhaar passing Verhoeff checksum validation."""
        digits = [self.fake.random.randint(0, 9) for _ in range(11)]
        for x in range(10):
            candidate = "".join(map(str, digits)) + str(x)
            if validate_verhoeff(candidate):
                return f"{candidate[:4]} {candidate[4:8]} {candidate[8:]}"
        return "1234 5678 9010"

    def get_mapping(self) -> dict:
        """Return a copy of the generated mapping dictionary."""
        return self._mappings.copy()

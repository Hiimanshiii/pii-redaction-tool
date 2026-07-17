import re
from dataclasses import dataclass
from typing import List
from collections import defaultdict
# pyrefly: ignore [missing-import]
import spacy

# Verhoeff algorithm tables for Aadhaar checksum validation
VERHOEFF_D = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
    [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]
]

VERHOEFF_P = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 2, 5, 8]
]

def validate_verhoeff(number: str) -> bool:
    """Validate number using Verhoeff algorithm."""
    num_str = re.sub(r'[\s-]', '', number)
    if not num_str.isdigit() or len(num_str) != 12:
        return False
    c = 0
    for i, item in enumerate(reversed(num_str)):
        c = VERHOEFF_D[c][VERHOEFF_P[i % 8][int(item)]]
    return c == 0

@dataclass
class DetectedEntity:
    """Represents a detected PII entity with its text, type, position, and confidence."""
    text: str
    entity_type: str
    start: int
    end: int
    confidence: float

class PIIDetector:
    """Detector for identifying structured PII and named entities (PERSON/COMPANY)."""

    def __init__(self) -> None:
        # Load spaCy model
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError as e:
            raise RuntimeError(
                "The spaCy model 'en_core_web_sm' is not installed. "
                "Please run: python -m spacy download en_core_web_sm"
            ) from e

        # Regex for standard emails
        self._email_regex = re.compile(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'
        )

        # Regexes for Indian mobile and landline phones, designed to avoid false positives
        self._phone_regexes = [
            # Mobile with +91 or 91 prefix, e.g. +91 9876543210, + 91 98765 43210, +91-9876543210
            re.compile(
                r'(?<!\d|\w)(?:\+\s*91|91)[\s-]*(?:[6-9]\d{4}[\s-]?\d{5}|[6-9]\d{9})(?!\d)'
            ),
            # Unprefixed 10-digit mobile starting with 6-9, e.g. 9876543210
            re.compile(
                r'(?<!\d)[6-9]\d{9}(?!\d)'
            ),
            # Landline with +91 or 91 prefix, e.g. +91 22 4009 4400, + 91 20 45053237
            re.compile(
                r'(?<!\d|\w)(?:\+\s*91|91)[\s-]*(?:[2-9]\d{1,3})[\s-]*(?:\d{4}[\s-]*\d{4}|\d{7,8})(?!\d)'
            )
        ]

        # Regex for IPv4 candidate addresses (four groups of 1-3 digits separated by dots)
        self._ip_regex = re.compile(
            r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'
        )

        # Regex for US SSN (XXX-XX-XXXX)
        self._ssn_regex = re.compile(
            r'\b\d{3}-\d{2}-\d{4}\b'
        )

        # Regex for credit card candidates (13-19 digits, optional spaces or hyphens)
        # Ensure it cannot start or end inside a longer numeric sequence
        self._cc_regex = re.compile(
            r'(?<!\d)\d(?:[\s-]?\d){12,18}(?!\d)'
        )

        # Set of forbidden words for named entities to exclude technical placeholder labels
        self._forbidden_entity_words = {
            "ssn", "ip", "email", "phone", "mobile", "section", "date",
            "card", "page", "number", "table", "prospectus"
        }

        # Set of company exclusions for generic false positives
        self._company_exclusions = {
            "indian securities", "proposed capital", "cash and bank",
            "public offer account bank", "the capital"
        }

        # Regex for PAN format (ABCDE1234F)
        self._pan_regex = re.compile(
            r'(?<!\d|[A-Za-z])[A-Za-z]{5}\d{4}[A-Za-z](?!\d|[A-Za-z])'
        )

        # Regex for AADHAAR candidate format
        self._aadhaar_regex = re.compile(
            r'(?<!\d)\d{4}[ -]?\d{4}[ -]?\d{4}(?!\d)'
        )

    def _is_valid_named_entity(self, text: str) -> bool:
        """Helper to validate if a text is a valid name or company."""
        val = text.strip()
        if not val or len(val) <= 1:
            return False
        
        # Must contain at least one alphabetic character
        if not any(c.isalpha() for c in val):
            return False
            
        # Ignore if it looks like an email
        if '@' in val:
            return False
            
        # Split into words and verify none is a forbidden placeholder word
        words = [w.strip(".,;:?!'\"()[]{}").lower() for w in val.split()]
        if any(w in self._forbidden_entity_words for w in words):
            return False
            
        return True

    def _detect_emails(self, text: str) -> List[DetectedEntity]:
        """Detect standard email formats."""
        entities = []
        for match in self._email_regex.finditer(text):
            entities.append(
                DetectedEntity(
                    text=match.group(),
                    entity_type="EMAIL",
                    start=match.start(),
                    end=match.end(),
                    confidence=1.0,
                )
            )
        return sorted(entities, key=lambda x: x.start)

    def _detect_phone_numbers(self, text: str) -> List[DetectedEntity]:
        """Detect Indian mobile and landline numbers while avoiding common false positives."""
        entities = []
        for idx, regex in enumerate(self._phone_regexes):
            for match in regex.finditer(text):
                # idx == 0 and idx == 2 are prefix-based (high confidence)
                # idx == 1 is unprefixed mobile (lower confidence)
                confidence = 0.9 if idx in (0, 2) else 0.7
                entities.append(
                    DetectedEntity(
                        text=match.group(),
                        entity_type="PHONE",
                        start=match.start(),
                        end=match.end(),
                        confidence=confidence,
                    )
                )
        return sorted(entities, key=lambda x: x.start)

    def _detect_ip_addresses(self, text: str) -> List[DetectedEntity]:
        """Detect IPv4 addresses and validate octet ranges (0-255)."""
        entities = []
        for match in self._ip_regex.finditer(text):
            match_str = match.group()
            try:
                octets = [int(o) for o in match_str.split('.')]
                if all(0 <= o <= 255 for o in octets):
                    entities.append(
                        DetectedEntity(
                            text=match_str,
                            entity_type="IP_ADDRESS",
                            start=match.start(),
                            end=match.end(),
                            confidence=1.0,
                        )
                    )
            except ValueError:
                continue
        return sorted(entities, key=lambda x: x.start)

    def _detect_ssns(self, text: str) -> List[DetectedEntity]:
        """Detect US SSNs (XXX-XX-XXXX) and filter out invalid patterns."""
        entities = []
        for match in self._ssn_regex.finditer(text):
            match_str = match.group()
            area, group, serial = match_str.split('-')
            
            if area == '000' or area == '666' or (900 <= int(area) <= 999):
                continue
            if group == '00':
                continue
            if serial == '0000':
                continue

            entities.append(
                DetectedEntity(
                    text=match_str,
                    entity_type="SSN",
                    start=match.start(),
                    end=match.end(),
                    confidence=1.0,
                )
            )
        return sorted(entities, key=lambda x: x.start)

    def _detect_credit_cards(self, text: str) -> List[DetectedEntity]:
        """Detect credit card candidates (13-19 digits) and validate using Luhn check."""
        entities = []
        for match in self._cc_regex.finditer(text):
            match_str = match.group()
            
            digits = [int(c) for c in match_str if c.isdigit()]
            if not (13 <= len(digits) <= 19):
                continue
                
            checksum = 0
            reverse_digits = digits[::-1]
            for i, d in enumerate(reverse_digits):
                if i % 2 == 1:
                    d *= 2
                    if d > 9:
                        d -= 9
                checksum += d
                
            if checksum % 10 == 0:
                entities.append(
                    DetectedEntity(
                        text=match_str,
                        entity_type="CREDIT_CARD",
                        start=match.start(),
                        end=match.end(),
                        confidence=1.0,
                    )
                )
        return sorted(entities, key=lambda x: x.start)

    def _detect_named_entities(self, text: str) -> List[DetectedEntity]:
        """Detect PERSON and ORG (mapped to COMPANY) entities using spaCy."""
        entities = []
        doc = self.nlp(text)
        for ent in doc.ents:
            val = ent.text.strip()
            if not self._is_valid_named_entity(val):
                continue

            if ent.label_ == "PERSON":
                # Confirm domain-specific exclusions
                person_exclusions = {
                    "reference rate", "selling shareholder", "key managerial personnel",
                    "mutual funds", "bid amount", "upi bidders", "registered broker",
                    "share transfer agents"
                }
                if val.lower() in person_exclusions:
                    continue

                # Reject location signals
                location_signals = ["taluka", "marg", "complex", "facility"]
                if any(sig in val.lower() for sig in location_signals):
                    continue

                # Strip trailing "Website" or "Company" from candidate
                cleaned_val = re.sub(r'\s+\b(?:website|company)\b\s*$', '', val, flags=re.IGNORECASE).strip()

                # Reject single-word PERSON detections
                if len(cleaned_val.split()) < 2:
                    continue
                # Reject PERSON candidates containing obvious non-name patterns
                if any(c.isdigit() for c in cleaned_val) or ":" in cleaned_val or "@" in cleaned_val:
                    continue
                # Reject candidates where all words are uppercase generic headings
                if cleaned_val.isupper():
                    continue

                entities.append(
                    DetectedEntity(
                        text=cleaned_val,
                        entity_type="PERSON",
                        start=ent.start_char,
                        end=ent.start_char + len(cleaned_val),
                        confidence=0.85
                    )
                )
            elif ent.label_ == "ORG":
                if val.lower() in self._company_exclusions:
                    continue
                entities.append(
                    DetectedEntity(
                        text=ent.text,
                        entity_type="COMPANY",
                        start=ent.start_char,
                        end=ent.end_char,
                        confidence=0.80
                    )
                )
        return sorted(entities, key=lambda x: x.start)

    def _detect_company_names_by_suffix(self, text: str) -> List[DetectedEntity]:
        """Detect company names by common suffixes with conservative boundary check."""
        entities = []
        pattern = re.compile(
            r'\b[A-Z0-9][A-Za-z0-9&]*(?:[ \t-]+(?:[A-Z0-9][A-Za-z0-9&]*|and|&))*[ \t]+'
            r'(?:Private Limited|PRIVATE LIMITED|Pvt\.\s*Ltd\.|PVT\.\s*LTD\.|Pvt\s*Ltd|PVT\s*LTD|Limited|LIMITED|Ltd\.|LTD\.|LLP|Bank|BANK|Securities|SECURITIES|Capital|CAPITAL|Industries|INDUSTRIES)\b'
        )
        for match in pattern.finditer(text):
            match_str = match.group()
            if match_str.lower() in self._company_exclusions:
                continue
            entities.append(
                DetectedEntity(
                    text=match_str,
                    entity_type="COMPANY",
                    start=match.start(),
                    end=match.end(),
                    confidence=0.90
                )
            )
        return sorted(entities, key=lambda x: x.start)

    def _detect_addresses(self, text: str) -> List[DetectedEntity]:
        """Detect Indian mailing/physical addresses conservatively."""
        val = text.strip()
        # Avoid long narrative paragraphs
        if not val or len(val) > 300:
            return []

        # Exclude leading contextual labels
        cleaned_val = val
        leading_regex = re.compile(
            r'^\s*(?:registered\s+office|corporate\s+office|registered\s+and\s+corporate\s+office)[\s\t:,-]*',
            re.IGNORECASE
        )
        leading_match = leading_regex.match(cleaned_val)
        if leading_match:
            cleaned_val = cleaned_val[leading_match.end():]

        # Prevent from consuming subsequent fields
        trailing_regex = re.compile(
            r'\b(?:Telephone|Email|E-mail|Website|Contact\s+Person)[\s\t:,-]',
            re.IGNORECASE
        )
        trailing_match = trailing_regex.search(cleaned_val)
        if trailing_match:
            cleaned_val = cleaned_val[:trailing_match.start()]

        cleaned_val = cleaned_val.strip()
        # Strip trailing punctuation commonly left over
        cleaned_val = cleaned_val.rstrip(";,.-")

        # Indicators
        indicators = {
            "road", "street", "marg", "lane", "building", "tower", "floor",
            "office", "plot", "village", "taluka", "nagar", "complex",
            "centre", "center", "pin", "pincode"
        }
        
        val_lower = cleaned_val.lower()
        matched_indicators = {ind for ind in indicators if ind in val_lower}
        
        # Indian PIN code detection (6 digits, not starting with 0)
        has_pin = bool(re.search(r'\b[1-9]\d{5}\b|\b[1-9]\d{2}\s+\d{3}\b', cleaned_val))
        
        is_address = False
        if len(matched_indicators) >= 2:
            is_address = True
        elif len(matched_indicators) >= 1 and has_pin:
            is_address = True
            
        if is_address:
            start = text.find(cleaned_val)
            if start != -1:
                end = start + len(cleaned_val)
                return [
                    DetectedEntity(
                        text=cleaned_val,
                        entity_type="ADDRESS",
                        start=start,
                        end=end,
                        confidence=0.90
                    )
                ]
        return []

    def _detect_dates_of_birth(self, text: str) -> List[DetectedEntity]:
        """Detect dates of birth close to explicit contextual keywords."""
        entities = []
        # Keywords
        keywords_pattern = r'\b(?:Date of Birth|DOB|D\.O\.B\.|Born)\b'
        
        # Supported date formats
        months = r'(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)'
        date_pattern = (
            r'(?:'
            r'\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b|'
            r'\b\d{4}-\d{2}-\d{2}\b|'
            r'\b' + months + r'\s+\d{1,2},\s*\d{4}\b|'
            r'\b\d{1,2}\s+' + months + r'\s+\d{4}\b'
            r')'
        )
        
        # Regex searching for keyword followed by optional symbols/spaces and date
        dob_regex = re.compile(
            r'(' + keywords_pattern + r')[\s\t:,-]{0,20}(' + date_pattern + r')',
            re.IGNORECASE
        )
        
        for match in dob_regex.finditer(text):
            date_text = match.group(2)
            start_offset = match.start(2)
            end_offset = match.end(2)
            
            # Double-check: reject if preceded by "Dated" (case-insensitive)
            pre_text = text[:match.start()].strip().lower()
            if pre_text.endswith("dated"):
                continue
                
            entities.append(
                DetectedEntity(
                    text=date_text,
                    entity_type="DATE_OF_BIRTH",
                    start=start_offset,
                    end=end_offset,
                    confidence=0.95
                )
            )
        return sorted(entities, key=lambda x: x.start)

    def _detect_pans(self, text: str) -> List[DetectedEntity]:
        """Detect Indian PAN card numbers (ABCDE1234F)."""
        entities = []
        for match in self._pan_regex.finditer(text):
            entities.append(
                DetectedEntity(
                    text=match.group(),
                    entity_type="PAN",
                    start=match.start(),
                    end=match.end(),
                    confidence=0.95
                )
            )
        return sorted(entities, key=lambda x: x.start)

    def _detect_aadhaars(self, text: str) -> List[DetectedEntity]:
        """Detect Indian Aadhaar card numbers validated by Verhoeff checksum."""
        entities = []
        for match in self._aadhaar_regex.finditer(text):
            match_str = match.group()
            if validate_verhoeff(match_str):
                entities.append(
                    DetectedEntity(
                        text=match_str,
                        entity_type="AADHAAR",
                        start=match.start(),
                        end=match.end(),
                        confidence=0.90
                    )
                )
        return sorted(entities, key=lambda x: x.start)

    def detect(self, text: str, min_confidence: float = 0.0) -> List[DetectedEntity]:
        """Detect all target PII types, sorting results, removing exact duplicates,

        resolving overlaps, and filtering by minimum confidence.

        Args:
            text (str): The text content to analyze.
            min_confidence (float): Minimum confidence threshold.

        Returns:
            List[DetectedEntity]: Sorted list of unique non-overlapping detected PII entities.
        """
        try:
            combined = []
            combined.extend(self._detect_emails(text))
            combined.extend(self._detect_phone_numbers(text))
            combined.extend(self._detect_ip_addresses(text))
            combined.extend(self._detect_ssns(text))
            combined.extend(self._detect_credit_cards(text))
            combined.extend(self._detect_named_entities(text))
            combined.extend(self._detect_company_names_by_suffix(text))
            combined.extend(self._detect_addresses(text))
            combined.extend(self._detect_dates_of_birth(text))
            combined.extend(self._detect_pans(text))
            combined.extend(self._detect_aadhaars(text))

            # 1. Resolve overlaps within the SAME entity type
            by_type = defaultdict(list)
            for entity in combined:
                by_type[entity.entity_type].append(entity)
                
            same_type_resolved = []
            for etype, entities_of_type in by_type.items():
                entities_of_type.sort(key=lambda x: (-(x.end - x.start), -x.confidence))
                accepted_for_type = []
                for entity in entities_of_type:
                    overlap = False
                    for accepted in accepted_for_type:
                        if max(entity.start, accepted.start) < min(entity.end, accepted.end):
                            overlap = True
                            break
                    if not overlap:
                        accepted_for_type.append(entity)
                same_type_resolved.extend(accepted_for_type)

            # 2. Resolve cross-type conflicts (exact same span)
            by_span = defaultdict(list)
            for entity in same_type_resolved:
                by_span[(entity.start, entity.end)].append(entity)

            def prefer_entity(e1: DetectedEntity, e2: DetectedEntity) -> DetectedEntity:
                structured_types = {
                    "AADHAAR", "PAN", "EMAIL", "PHONE", "IP_ADDRESS", "SSN",
                    "CREDIT_CARD", "ADDRESS", "DATE_OF_BIRTH"
                }
                ner_types = {"PERSON", "COMPANY"}
                
                if e1.entity_type in structured_types and e2.entity_type in ner_types:
                    return e1
                if e2.entity_type in structured_types and e1.entity_type in ner_types:
                    return e2

                is_suffix_co_1 = (e1.entity_type == "COMPANY" and abs(e1.confidence - 0.90) < 1e-5)
                is_suffix_co_2 = (e2.entity_type == "COMPANY" and abs(e2.confidence - 0.90) < 1e-5)
                is_person_1 = (e1.entity_type == "PERSON")
                is_person_2 = (e2.entity_type == "PERSON")
                
                if is_suffix_co_1 and is_person_2:
                    return e1
                if is_suffix_co_2 and is_person_1:
                    return e2
                    
                if e1.confidence != e2.confidence:
                    return e1 if e1.confidence > e2.confidence else e2
                if e1.entity_type == "COMPANY":
                    return e1
                return e2

            final_entities = []
            for span, entities_in_span in by_span.items():
                preferred = entities_in_span[0]
                for other in entities_in_span[1:]:
                    preferred = prefer_entity(preferred, other)
                final_entities.append(preferred)

            # Filter by minimum confidence
            if min_confidence > 0.0:
                final_entities = [e for e in final_entities if e.confidence >= min_confidence]

            # Final sort by start position to return in document order
            final_entities.sort(key=lambda x: x.start)
            return final_entities
        except Exception as e:
            raise RuntimeError("An unexpected error occurred during PII detection.") from e

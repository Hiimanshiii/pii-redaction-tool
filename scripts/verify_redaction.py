import os
import sys
from pathlib import Path
from collections import defaultdict
from src.document_processor import DocumentProcessor
from src.detectors import PIIDetector

def main():
    input_path = "input/Red Herring Prospectus.docx"
    output_path = "output/redacted_prospectus.docx"

    print("PII Redaction Verification")
    print("--------------------------")
    print(f"Original: {input_path}")
    print(f"Redacted: {output_path}\n")

    # 1. Confirm both files exist
    if not os.path.exists(input_path):
        print(f"FAIL: Original file not found at {input_path}")
        sys.exit(1)
    if not os.path.exists(output_path):
        print(f"FAIL: Redacted file not found at {output_path}")
        sys.exit(1)

    print("1. File Existence: PASS")

    # Load documents
    original_processor = DocumentProcessor(input_path)
    redacted_processor = DocumentProcessor(output_path)
    
    try:
        original_processor.load_document()
        redacted_processor.load_document()
    except Exception as e:
        print(f"FAIL: Error loading documents: {e}")
        sys.exit(1)

    original_text = original_processor.extract_text()
    redacted_text = redacted_processor.extract_text()

    # 2. Check that known original PII values no longer appear in the redacted text
    known_pii_checks = [
        "Sarthak Malvadkar",
        "cs.connect@kshinternational.com",
        "Sarthak.malvadkar@kshinterantional.com"
    ]

    print("\n2. Verification of Original PII Removal:")
    pii_removal_ok = True
    for pii in known_pii_checks:
        # Check if it was in the original text (for context)
        was_in_original = pii.lower() in original_text.lower()
        is_in_redacted = pii.lower() in redacted_text.lower()
        
        status = "REMOVED (PASS)" if not is_in_redacted else "STILL PRESENT (FAIL)"
        if is_in_redacted:
            pii_removal_ok = False
            
        print(f"  - '{pii}': {status} (Was in original: {was_in_original})")

    if pii_removal_ok:
        print("  => PII Removal Status: PASS")
    else:
        print("  => PII Removal Status: FAIL")

    # 3. Check that important non-PII text still exists
    non_pii_checks = [
        "RED HERRING PROSPECTUS",
        "Companies Act",
        "Book Built Offer"
    ]

    print("\n3. Verification of Non-PII Text Preservation:")
    non_pii_ok = True
    for term in non_pii_checks:
        is_in_redacted = term.lower() in redacted_text.lower()
        status = "PRESERVED (PASS)" if is_in_redacted else "MISSING (FAIL)"
        if not is_in_redacted:
            non_pii_ok = False
        print(f"  - '{term}': {status}")

    if non_pii_ok:
        print("  => Non-PII Preservation Status: PASS")
    else:
        print("  => Non-PII Preservation Status: FAIL")

    # 4. Run PIIDetector on the redacted document text chunks to count PII-like replacements
    print("\n4. PII-like Entities Detected in Redacted Document:")
    detector = PIIDetector()
    chunks = redacted_processor.get_text_chunks()
    
    redacted_detections = []
    for chunk in chunks:
        # Run detection using the same min_confidence used in redaction
        entities = detector.detect(chunk, min_confidence=0.85)
        redacted_detections.extend(entities)

    counts_by_type = defaultdict(int)
    for entity in redacted_detections:
        counts_by_type[entity.entity_type] += 1

    print(f"  Total PII-like detections in output: {len(redacted_detections)}")
    target_types = [
        "EMAIL", "PHONE", "IP_ADDRESS", "SSN", "CREDIT_CARD",
        "PERSON", "COMPANY", "ADDRESS", "DATE_OF_BIRTH", "PAN", "AADHAAR"
    ]
    for t in target_types:
        print(f"    - {t}: {counts_by_type[t]} detections")

    print("\nVerification completed.")
    if pii_removal_ok and non_pii_ok:
        print("Overall Redaction Validation: PASS")
        sys.exit(0)
    else:
        print("Overall Redaction Validation: FAIL")
        sys.exit(1)

if __name__ == "__main__":
    main()

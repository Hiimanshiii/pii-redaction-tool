import sys
from src.docx_redactor import DocxRedactor

def main():
    input_path = "input/Red Herring Prospectus.docx"
    output_path = "output/redacted_prospectus.docx"

    print("PII Redaction Tool")
    print("------------------")
    print(f"Input: {input_path}")
    print(f"Output: {output_path}\n")

    print("Processing document...")
    try:
        redactor = DocxRedactor(
            input_path=input_path,
            output_path=output_path,
            min_confidence=0.85
        )
        redactor.redact_document()
        
        print("\nRedaction completed successfully.\n")

        # Retrieve and display statistics
        stats = redactor.get_statistics()
        print("Redaction Summary:")
        print(f"Total redactions: {stats['total_redactions']}")
        
        target_types = [
            "EMAIL", "PHONE", "IP_ADDRESS", "SSN", "CREDIT_CARD",
            "PERSON", "COMPANY", "ADDRESS", "DATE_OF_BIRTH", "PAN", "AADHAAR"
        ]
        
        counts = stats["counts_by_type"]
        unique_counts = stats["unique_counts_by_type"]
        
        for t in target_types:
            cnt = counts.get(t, 0)
            uniq = unique_counts.get(t, 0)
            print(f"- {t}: {cnt} redactions ({uniq} unique)")

        print()
        
        # Post-redaction rescan validation
        validation = redactor.validate_redaction()
        status_str = "PASSED" if validation["passed"] else "FAILED"
        print(f"Post-redaction validation: {status_str}")
        print(f"Potential original PII values remaining: {validation['potential_leaks']}")
            
    except FileNotFoundError as e:
        print(f"\nError: File not found: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"\nError: Invalid argument: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\nAn error occurred during redaction: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()

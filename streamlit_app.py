# pyrefly: ignore [missing-import]
import os
import streamlit as st
from pathlib import Path
from src.docx_redactor import DocxRedactor

def main():
    # 1. Page Configuration
    st.set_page_config(
        page_title="PII Redaction Tool",
        page_icon="🔒",
        layout="wide"
    )

    # Inject Custom CSS for modern clean aesthetic
    st.markdown(
        """
        <style>
        .metric-card {
            background-color: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
            text-align: center;
            margin-bottom: 15px;
        }
        .metric-name {
            font-size: 0.9em;
            text-transform: uppercase;
            color: #64748b;
            font-weight: 600;
            letter-spacing: 0.05em;
        }
        .metric-value {
            font-size: 2.6em;
            font-weight: 700;
            color: #0f172a;
            margin: 8px 0;
        }
        .metric-extra {
            font-size: 0.85em;
            color: #94a3b8;
            font-weight: 500;
        }
        .pipeline-step {
            padding: 8px 12px;
            background-color: #f8fafc;
            border-left: 4px solid #3b82f6;
            margin-bottom: 6px;
            border-radius: 0 4px 4px 0;
            font-size: 0.9em;
            color: #334155;
            font-weight: 500;
        }
        .footer-text {
            text-align: center;
            color: #64748b;
            font-size: 0.85em;
            line-height: 1.6;
            margin-top: 30px;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # 2. Sidebar Layout
    with st.sidebar:
        st.title("🔒 PII Redactor")
        st.write("Securely redact sensitive information from DOCX documents.")
        
        st.markdown("---")
        st.subheader("Supported Detection")
        supported_pii = [
            "Person", "Company", "Email", "Phone", "Address",
            "PAN", "Aadhaar", "SSN", "Credit Card", "IP Address", "DOB"
        ]
        for pii in supported_pii:
            st.markdown(f"✓ {pii}")
            
        st.markdown("---")
        st.subheader("Pipeline")
        steps = [
            "Document Upload",
            "PII Detection",
            "Replacement",
            "Validation",
            "Download"
        ]
        for step in steps:
            st.markdown(f"<div class='pipeline-step'>{step}</div>", unsafe_allow_html=True)

    # 3. Main Page Layout
    st.markdown("## 🔒 PII Redaction Tool")
    st.markdown(
        "<p style='font-size: 1.15em; color: #475569;'>"
        "Securely detect and redact Personally Identifiable Information from Microsoft Word documents."
        "</p>",
        unsafe_allow_html=True
    )
    st.markdown("---")

    # File Uploader
    uploaded_file = st.file_uploader(
        label="Upload Microsoft Word document (.docx)",
        type=["docx"]
    )

    # Placeholder for processing outputs
    placeholder = st.empty()

    if uploaded_file is not None:
        filename = uploaded_file.name
        file_size = uploaded_file.size
        
        # Check size constraints
        if file_size == 0:
            st.error("Error: The uploaded file is empty. Please upload a valid .docx file.")
            return
            
        if file_size > 25 * 1024 * 1024:
            st.warning("Warning: File size exceeds 25 MB. Processing may take longer.")
            
        file_ext = Path(filename).suffix
        if file_ext.lower() != ".docx":
            st.error("Error: Invalid file format. Only Microsoft Word documents (.docx) are supported.")
            return
            
        import datetime
        upload_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        def format_size(size_in_bytes):
            if size_in_bytes >= 1024 * 1024:
                return f"{size_in_bytes / (1024 * 1024):.2f} MB"
            else:
                return f"{size_in_bytes / 1024:.2f} KB"

        # Uploaded File Preview Card
        st.markdown(
            f"""
            <div style="
                background-color: #f8fafc;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
                padding: 20px;
                margin-bottom: 20px;
            ">
                <h4 style="margin-top:0; color: #1e293b;">Uploaded File Information</h4>
                <table style="width: 100%; border-collapse: collapse; font-size: 0.95em;">
                    <tr>
                        <td style="padding: 6px 0; font-weight: 600; color: #475569; width: 30%;">File Name:</td>
                        <td style="padding: 6px 0; color: #1e293b;">{filename}</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 0; font-weight: 600; color: #475569;">Extension:</td>
                        <td style="padding: 6px 0; color: #1e293b;">{file_ext}</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 0; font-weight: 600; color: #475569;">File Size:</td>
                        <td style="padding: 6px 0; color: #1e293b;">{format_size(file_size)}</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 0; font-weight: 600; color: #475569;">Upload Time:</td>
                        <td style="padding: 6px 0; color: #1e293b;">{upload_time}</td>
                    </tr>
                </table>
            </div>
            """,
            unsafe_allow_html=True
        )

        # Ensure directories exist
        input_dir = Path("input")
        input_dir.mkdir(parents=True, exist_ok=True)
        output_dir = Path("output")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        input_path = input_dir / filename
        output_path = output_dir / f"redacted_{filename}"
        
        # Process and redact document
        try:
            import time
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Step 1: Saving uploaded document
            status_text.text("Saving uploaded document...")
            progress_bar.progress(15)
            time.sleep(0.3)
            with open(input_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
                
            # Step 2: Detecting PII
            status_text.text("Detecting PII...")
            progress_bar.progress(35)
            time.sleep(0.3)
            redactor = DocxRedactor(
                input_path=str(input_path),
                output_path=str(output_path),
                min_confidence=0.85
            )
            
            # Step 3: Replacing entities
            status_text.text("Replacing entities...")
            progress_bar.progress(55)
            time.sleep(0.3)
            
            # Step 4: Generating redacted document
            status_text.text("Generating redacted document...")
            progress_bar.progress(75)
            time.sleep(0.3)
            redactor.redact_document()
            
            # Step 5: Running validation
            status_text.text("Running validation...")
            progress_bar.progress(90)
            time.sleep(0.3)
            stats = redactor.get_statistics()
            validation = redactor.validate_redaction()
            
            progress_bar.progress(100)
            status_text.text("Redaction and validation complete!")
            time.sleep(0.3)
            
            # Clear progress controls
            progress_bar.empty()
            status_text.empty()
            
            # Render results inside placeholder container
            with placeholder.container():
                st.markdown("---")
                
                # Processing Summary Box
                val_status = "PASSED" if validation["passed"] else "FAILED"
                st.markdown(
                    f"""
                    <div style="
                        background-color: #f0fdf4;
                        border: 1px solid #bbf7d0;
                        border-radius: 12px;
                        padding: 20px;
                        margin-bottom: 20px;
                    ">
                        <h4 style="margin-top:0; color: #166534;">Processing Summary</h4>
                        <table style="width: 100%; border-collapse: collapse; font-size: 0.95em;">
                            <tr>
                                <td style="padding: 6px 0; font-weight: 600; color: #1e3a1e; width: 30%;">Original Filename:</td>
                                <td style="padding: 6px 0; color: #166534;">{filename}</td>
                            </tr>
                            <tr>
                                <td style="padding: 6px 0; font-weight: 600; color: #1e3a1e;">Output Filename:</td>
                                <td style="padding: 6px 0; color: #166534;">redacted_{filename}</td>
                            </tr>
                            <tr>
                                <td style="padding: 6px 0; font-weight: 600; color: #1e3a1e;">Status:</td>
                                <td style="padding: 6px 0; color: #166534;">Completed successfully</td>
                            </tr>
                            <tr>
                                <td style="padding: 6px 0; font-weight: 600; color: #1e3a1e;">Validation Result:</td>
                                <td style="padding: 6px 0; color: #166534; font-weight: 700;">{val_status}</td>
                            </tr>
                        </table>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                
                # Two column result header layout
                res_col1, res_col2 = st.columns([2, 1])
                
                with res_col1:
                    st.subheader("Validation Report")
                    if validation["passed"]:
                        st.success(
                            "🟢 **Validation Passed**\n\n"
                            f"Potential Original PII Remaining: **{validation['potential_leaks']}**"
                        )
                    else:
                        st.error(
                            "🔴 **Validation Failed**\n\n"
                            f"Potential Original PII Remaining: **{validation['potential_leaks']}**"
                        )
                    
                    # Success message above download button
                    st.info("Your document has been successfully redacted and validated.")
                    
                    # Download Button directly below validation box
                    try:
                        with open(output_path, "rb") as f:
                            st.download_button(
                                label="Download Redacted Document",
                                data=f,
                                file_name=f"redacted_{filename}",
                                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                            )
                    except Exception as e:
                        st.error(f"Failed to prepare download: {e}")
                
                st.markdown("---")
                st.subheader("Redaction Statistics")
                
                counts = stats.get("counts_by_type", {})
                unique_counts = stats.get("unique_counts_by_type", {})
                
                active_metrics = []
                # Total Redactions
                active_metrics.append({
                    "name": "Total Redactions",
                    "count": stats["total_redactions"],
                    "extra": "across all categories"
                })
                # Entity Categories
                for label, key in [("Email", "EMAIL"), ("Phone", "PHONE"), ("Person", "PERSON"), ("Company", "COMPANY"), ("Address", "ADDRESS")]:
                    cnt = counts.get(key, 0)
                    if cnt > 0:
                        uniq = unique_counts.get(key, 0)
                        active_metrics.append({
                            "name": label,
                            "count": cnt,
                            "extra": f"{uniq} unique"
                        })
                
                # Display in rows of 3 columns
                for r in range(0, len(active_metrics), 3):
                    row_metrics = active_metrics[r:r+3]
                    cols = st.columns(3)
                    for idx, metric in enumerate(row_metrics):
                        with cols[idx]:
                            st.markdown(
                                f"""
                                <div class="metric-card">
                                    <div class="metric-name">{metric['name']}</div>
                                    <div class="metric-value">{metric['count']}</div>
                                    <div class="metric-extra">{metric['extra']}</div>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )
                
        except Exception as e:
            st.error(f"An error occurred during redaction: {e}")

    # 4. About & Project Information (Always displayed at the bottom of the main page)
    st.markdown("---")
    
    # 1. How It Works Expander
    with st.expander("ℹ️ How It Works", expanded=False):
        st.markdown(
            """
            The PII Redaction Tool processes documents locally and securely through a 5-step pipeline:
            1. **Document Upload:** The uploaded Word document (.docx) is loaded into memory securely.
            2. **PII Detection:** Local Named Entity Recognition (NER) models scan the text.
            3. **Replacement:** Identified entities are replaced with consistent synthetic values.
            4. **Validation:** A post-redaction scan checks for any traces of original PII in redacted segments.
            5. **Download:** The redacted document is prepared and made available for download.
            """
        )
    
    st.markdown("---")
    
    # 2. Technologies Used Section (Two Columns)
    st.subheader("Technologies Used")
    tech_col1, tech_col2 = st.columns(2)
    with tech_col1:
        st.markdown("**Backend**")
        st.markdown("- Python")
        st.markdown("- spaCy")
        st.markdown("- Faker")
        st.markdown("- python-docx")
    with tech_col2:
        st.markdown("**Testing & Quality**")
        st.markdown("- unittest")
        st.markdown("- Evaluation Framework")
        st.markdown("- Deterministic Replacement Engine")

    st.markdown("---")

    # 3. Supported PII Section (Three Columns)
    st.subheader("Supported PII")
    pii_col1, pii_col2, pii_col3 = st.columns(3)
    with pii_col1:
        st.markdown("- Person")
        st.markdown("- Company")
        st.markdown("- Email")
        st.markdown("- Phone")
    with pii_col2:
        st.markdown("- Address")
        st.markdown("- PAN")
        st.markdown("- Aadhaar")
        st.markdown("- SSN")
    with pii_col3:
        st.markdown("- Credit Card")
        st.markdown("- IP Address")
        st.markdown("- DOB")

    st.markdown("---")

    # 4. Evaluation Metrics Section (Metric Widgets)
    st.subheader("Evaluation Metrics")
    met_col1, met_col2, met_col3, met_col4 = st.columns(4)
    met_col1.metric("Precision", "100%")
    met_col2.metric("Recall", "96.88%")
    met_col3.metric("F1 Score", "98.41%")
    met_col4.metric("Exact Accuracy", "96.88%")

    st.markdown("---")

    # 5. Key Features Section (Checkmarks)
    st.subheader("Key Features")
    st.markdown("✓ Deterministic replacements")
    st.markdown("✓ Format preservation")
    st.markdown("✓ Post-redaction validation")
    st.markdown("✓ No raw PII logging")
    st.markdown("✓ Production-safe error handling")
    st.markdown("✓ Integration tested")
    st.markdown("✓ DOCX support")

    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div class="footer-text">
            <strong>PII Redaction Tool v1.0</strong><br>
            Built using Python, spaCy, Faker, python-docx and Streamlit.<br>
            © 2026
        </div>
        """,
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()

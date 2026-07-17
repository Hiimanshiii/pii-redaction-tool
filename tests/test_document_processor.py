import unittest
from src.document_processor import DocumentProcessor

class TestDocumentProcessor(unittest.TestCase):
    def test_unloaded_document_raises_value_error(self):
        processor = DocumentProcessor("input/Red Herring Prospectus.docx")
        # Should raise ValueError before load_document is called
        with self.assertRaises(ValueError):
            processor.get_text_chunks()

    def test_load_and_chunks(self):
        processor = DocumentProcessor("input/Red Herring Prospectus.docx")
        processor.load_document()
        
        # Verify stats and text chunks
        stats = processor.get_statistics()
        chunks = processor.get_text_chunks()
        
        self.assertIsInstance(chunks, list)
        self.assertTrue(len(chunks) > 0)
        
        # Verify that total chunks corresponds to non_empty_paragraphs + unique cells in tables
        # Let's count unique cells in tables from stats:
        # non_empty_paragraphs is paragraph chunks.
        # Unique table cells with non-empty text:
        # Let's compute expected count manually by repeating the logic
        expected_p_chunks = sum(1 for p in processor.document.paragraphs if p.text.strip())
        
        expected_cell_chunks = 0
        for table in processor.document.tables:
            seen_cells = set()
            for row in table.rows:
                for cell in row.cells:
                    if cell._tc not in seen_cells:
                        seen_cells.add(cell._tc)
                        if cell.text.strip():
                            expected_cell_chunks += 1
                            
        self.assertEqual(len(chunks), expected_p_chunks + expected_cell_chunks)

    def test_load_document_validation_errors(self) -> None:
        import os
        import tempfile

        # 1. Non-existent file
        processor_missing = DocumentProcessor("nonexistent_file_path.docx")
        with self.assertRaises(FileNotFoundError):
            processor_missing.load_document()

        # 2. Directory instead of file
        with tempfile.TemporaryDirectory() as temp_dir:
            processor_dir = DocumentProcessor(temp_dir)
            with self.assertRaises(ValueError):
                processor_dir.load_document()

            # 3. Unsupported extension
            invalid_ext_path = os.path.join(temp_dir, "test.txt")
            with open(invalid_ext_path, "w") as f:
                f.write("some text")
            processor_ext = DocumentProcessor(invalid_ext_path)
            with self.assertRaises(ValueError):
                processor_ext.load_document()

            # 4. Corrupted/unreadable docx
            corrupt_path = os.path.join(temp_dir, "corrupt.docx")
            with open(corrupt_path, "wb") as f:
                f.write(b"invalid corrupt zip bytes sequence")
            processor_corrupt = DocumentProcessor(corrupt_path)
            with self.assertRaises(ValueError):
                processor_corrupt.load_document()

if __name__ == '__main__':
    unittest.main()

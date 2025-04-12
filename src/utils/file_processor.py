import os
from typing import Dict, Any, Optional
import PyPDF2
from PIL import Image
import io

from utils.gemini_service import GeminiService

class FileProcessor:
    """Service for processing different file types (images, PDFs) for donation extraction."""
    
    def __init__(self, gemini_service: GeminiService):
        """Initialize the file processor with a Gemini service."""
        self.gemini_service = gemini_service
    
    def process(self, file_path: str, file_ext: str) -> Optional[Dict[str, Any]]:
        """Process a file to extract donation information.
        
        Args:
            file_path: Path to the file
            file_ext: File extension (.jpg, .png, .pdf, etc.)
            
        Returns:
            Dictionary containing extracted donation data or None if extraction failed
        """
        if file_ext in ['.jpg', '.jpeg', '.png']:
            return self._process_image(file_path)
        elif file_ext == '.pdf':
            return self._process_pdf(file_path)
        else:
            print(f"Unsupported file type: {file_ext}")
            return None
    
    def _process_image(self, image_path: str) -> Optional[Dict[str, Any]]:
        """Process an image file.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Dictionary containing extracted donation data or None if extraction failed
        """
        try:
            # Simple validation of image before sending to Gemini
            img = Image.open(image_path)
            img.verify()  # Check if it's a valid image
            
            # Extract donation data using Gemini
            donation_data = self.gemini_service.extract_donation_data(image_path)
            return donation_data
        
        except Exception as e:
            print(f"Error processing image {image_path}: {str(e)}")
            return None
    
    def _process_pdf(self, pdf_path: str) -> Optional[Dict[str, Any]]:
        """Process a PDF file.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Dictionary containing extracted donation data or None if extraction failed
        """
        try:
            # For simplicity, convert the first page of the PDF to an image
            # and then process it using Gemini
            
            # Extract first page as image
            with open(pdf_path, 'rb') as pdf_file:
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                if len(pdf_reader.pages) > 0:
                    # Convert PDF page to image (requires additional libraries in production)
                    # For now, just pass the PDF directly to Gemini
                    donation_data = self.gemini_service.extract_donation_data(pdf_path)
                    return donation_data
                else:
                    print(f"PDF file {pdf_path} has no pages")
                    return None
        
        except Exception as e:
            print(f"Error processing PDF {pdf_path}: {str(e)}")
            return None
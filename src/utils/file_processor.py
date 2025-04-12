import os
from typing import Dict, Any, Optional, List, Union
import PyPDF2
from PIL import Image
import io

from utils.gemini_service import GeminiService

class FileProcessor:
    """Service for processing different file types (images, PDFs) for donation extraction."""
    
    def __init__(self, gemini_service: GeminiService):
        """Initialize the file processor with a Gemini service."""
        self.gemini_service = gemini_service
    
    def process(self, file_path: str, file_ext: str) -> Any:
        """Process a file to extract donation information.
        
        Args:
            file_path: Path to the file
            file_ext: File extension (.jpg, .png, .pdf, etc.)
            
        Returns:
            Dictionary containing extracted donation data or 
            List of dictionaries (for PDFs with multiple donations) or None if extraction failed
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
    
    def _process_pdf(self, pdf_path: str) -> Optional[Union[Dict[str, Any], List[Dict[str, Any]]]]:
        """Process a PDF file.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Dictionary containing extracted donation data,
            List of dictionaries (for PDFs with multiple donations),
            or None if extraction failed
        """
        try:
            # Send PDF directly to Gemini for processing
            donation_data = self.gemini_service.extract_donation_data(pdf_path)
            return donation_data
        
        except Exception as e:
            print(f"Error processing PDF {pdf_path}: {str(e)}")
            return None
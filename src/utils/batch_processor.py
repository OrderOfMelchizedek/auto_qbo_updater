"""Concurrent batch processor for file processing."""
import os
import io
import gc
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional, Tuple, Union
from dataclasses import dataclass
import PyPDF2
import fitz  # PyMuPDF
from PIL import Image

from .gemini_service import GeminiService
from .progress_logger import ProgressLogger
from .memory_monitor import memory_monitor


@dataclass
class ProcessingBatch:
    """Represents a batch of content to process."""
    batch_id: str
    batch_type: str  # 'pdf', 'image', 'csv'
    file_path: str
    content: Any  # Can be images, text, or file path
    page_numbers: Optional[List[int]] = None  # For PDFs
    metadata: Optional[Dict[str, Any]] = None


class BatchProcessor:
    """Handles concurrent batch processing of files."""
    
    # Configuration
    PDF_BATCH_SIZE = 10  # Pages per PDF batch
    MAX_CONCURRENT_BATCHES = 10  # Maximum concurrent API calls
    
    def __init__(self, gemini_service: GeminiService, progress_logger: Optional[ProgressLogger] = None):
        """Initialize the batch processor.
        
        Args:
            gemini_service: The Gemini service instance for API calls
            progress_logger: Optional progress logger for tracking
        """
        self.gemini_service = gemini_service
        self.progress_logger = progress_logger
        self._semaphore = threading.Semaphore(self.MAX_CONCURRENT_BATCHES)
        
    def prepare_batches(self, files: List[Tuple[str, str]]) -> List[ProcessingBatch]:
        """Prepare batches from a list of files.
        
        Args:
            files: List of tuples (file_path, file_type)
            
        Returns:
            List of ProcessingBatch objects ready for concurrent processing
        """
        batches = []
        
        for file_path, file_type in files:
            if file_type == '.pdf':
                # Create batches for PDF
                pdf_batches = self._prepare_pdf_batches(file_path)
                batches.extend(pdf_batches)
            elif file_type in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']:
                # Each image is its own batch
                batch = ProcessingBatch(
                    batch_id=f"img_{os.path.basename(file_path)}",
                    batch_type='image',
                    file_path=file_path,
                    content=file_path
                )
                batches.append(batch)
            elif file_type == '.csv':
                # Each CSV is its own batch
                batch = ProcessingBatch(
                    batch_id=f"csv_{os.path.basename(file_path)}",
                    batch_type='csv',
                    file_path=file_path,
                    content=file_path
                )
                batches.append(batch)
                
        return batches
    
    def _prepare_pdf_batches(self, pdf_path: str) -> List[ProcessingBatch]:
        """Prepare PDF batches with 2 pages each.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            List of ProcessingBatch objects for the PDF
        """
        batches = []
        pdf_doc = None
        
        try:
            # Open PDF to get page count
            pdf_doc = fitz.open(pdf_path)
            total_pages = len(pdf_doc)
            
            # Create batches of 10 pages each
            for batch_start in range(0, total_pages, self.PDF_BATCH_SIZE):
                batch_end = min(batch_start + self.PDF_BATCH_SIZE, total_pages)
                page_numbers = list(range(batch_start, batch_end))
                
                batch = ProcessingBatch(
                    batch_id=f"pdf_{os.path.basename(pdf_path)}_pages_{batch_start+1}-{batch_end}",
                    batch_type='pdf',
                    file_path=pdf_path,
                    content=None,  # Will be populated during processing
                    page_numbers=page_numbers,
                    metadata={'total_pages': total_pages}
                )
                batches.append(batch)
                
        except Exception as e:
            print(f"Error preparing PDF batches for {pdf_path}: {str(e)}")
        finally:
            # Always close the PDF document
            if pdf_doc:
                pdf_doc.close()
                del pdf_doc
                gc.collect()
            
        return batches
    
    def process_batches_concurrently(self, batches: List[ProcessingBatch], 
                                   task_id: Optional[str] = None) -> Tuple[List[Dict[str, Any]], List[str]]:
        """Process all batches concurrently.
        
        Args:
            batches: List of ProcessingBatch objects to process
            task_id: Optional task ID for progress tracking
            
        Returns:
            Tuple of (donations, errors)
        """
        all_donations = []
        all_errors = []
        processed_count = 0
        total_batches = len(batches)
        
        # Update initial progress
        if self.progress_logger and task_id:
            self.progress_logger.log(
                f"Processing {total_batches} batches concurrently"
            )
        
        # Process batches concurrently
        with ThreadPoolExecutor(max_workers=self.MAX_CONCURRENT_BATCHES) as executor:
            # Submit all batches for processing
            future_to_batch = {
                executor.submit(self._process_single_batch, batch): batch 
                for batch in batches
            }
            
            # Process completed batches as they finish
            for future in as_completed(future_to_batch):
                batch = future_to_batch[future]
                
                try:
                    donations, errors = future.result()
                    
                    # Aggregate results
                    if donations:
                        all_donations.extend(donations if isinstance(donations, list) else [donations])
                    if errors:
                        all_errors.extend(errors if isinstance(errors, list) else [errors])
                        
                    # Update progress
                    processed_count += 1
                    if self.progress_logger and task_id:
                        self.progress_logger.log(
                            f"Processed {processed_count}/{total_batches} batches"
                        )
                        
                except Exception as e:
                    error_msg = f"Error processing batch {batch.batch_id}: {str(e)}"
                    print(error_msg)
                    all_errors.append(error_msg)
                    
                    # Still update progress on error
                    processed_count += 1
                    if self.progress_logger and task_id:
                        self.progress_logger.log(
                            f"Processed {processed_count}/{total_batches} batches (with errors)"
                        )
        
        # Final progress update
        if self.progress_logger and task_id:
            self.progress_logger.log(
                f"Completed processing {total_batches} batches"
            )
        
        return all_donations, all_errors
    
    def _process_single_batch(self, batch: ProcessingBatch) -> Tuple[List[Dict[str, Any]], List[str]]:
        """Process a single batch.
        
        Args:
            batch: The ProcessingBatch to process
            
        Returns:
            Tuple of (donations, errors)
        """
        donations = []
        errors = []
        
        # Acquire semaphore to limit concurrent API calls
        with self._semaphore:
            try:
                if batch.batch_type == 'pdf':
                    result = self._process_pdf_batch(batch)
                elif batch.batch_type == 'image':
                    result = self.gemini_service.extract_donation_data(batch.file_path)
                elif batch.batch_type == 'csv':
                    result = self.gemini_service.extract_text_data(batch.file_path, file_type='csv')
                else:
                    raise ValueError(f"Unknown batch type: {batch.batch_type}")
                
                # Handle results
                if result:
                    if isinstance(result, list):
                        donations.extend(result)
                    else:
                        donations.append(result)
                        
            except Exception as e:
                error_msg = f"Error in batch {batch.batch_id}: {str(e)}"
                print(error_msg)
                errors.append(error_msg)
                
        return donations, errors
    
    @memory_monitor.monitor_function
    def _process_pdf_batch(self, batch: ProcessingBatch) -> Optional[Union[Dict[str, Any], List[Dict[str, Any]]]]:
        """Process a PDF batch with its pages, images, and text.
        
        Args:
            batch: The PDF batch to process
            
        Returns:
            Extracted donation data or None
        """
        pdf_doc = None
        pdf_reader = None
        images = []
        
        try:
            # Open PDF document
            pdf_doc = fitz.open(batch.file_path)
            
            # Extract text from the batch pages
            batch_text = ""
            try:
                pdf_reader = PyPDF2.PdfReader(batch.file_path)
                for page_num in batch.page_numbers:
                    if page_num < len(pdf_reader.pages):
                        page_text = pdf_reader.pages[page_num].extract_text()
                        if page_text:
                            batch_text += f"\n--- Page {page_num + 1} ---\n{page_text}\n"
            except Exception as e:
                print(f"Error extracting text from PDF pages: {str(e)}")
            finally:
                # Clean up PDF reader
                if pdf_reader:
                    del pdf_reader
            
            # Convert pages to images
            for page_num in batch.page_numbers:
                page = pdf_doc[page_num]
                # Convert page to image with good resolution
                pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))  # 1.5x zoom
                img_data = pix.tobytes("png")
                image = Image.open(io.BytesIO(img_data))
                images.append(image)
                # Clean up pixmap immediately
                del pix
                del img_data
            
            # Prepare content for Gemini
            content = {
                'images': images,
                'text': batch_text if batch_text.strip() else None,
                'page_info': f"Pages {batch.page_numbers[0]+1} to {batch.page_numbers[-1]+1} of {batch.metadata.get('total_pages', 'unknown')}"
            }
            
            # Call Gemini with the prepared content
            result = self.gemini_service.extract_donation_data_from_content(
                content,
                file_type='pdf_batch',
                batch_info=batch.batch_id
            )
            
            return result
            
        except Exception as e:
            print(f"Error processing PDF batch {batch.batch_id}: {str(e)}")
            return None
        finally:
            # Clean up resources
            if pdf_doc:
                pdf_doc.close()
                del pdf_doc
            
            # Clean up images
            for img in images:
                if hasattr(img, 'close'):
                    img.close()
            del images
            
            # Force garbage collection
            gc.collect()
            
            print(f"Batch {batch.batch_id} processed - memory cleaned up")
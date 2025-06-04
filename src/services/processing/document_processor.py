"""Document processing service for converting documents to images."""
import io
import logging
import tempfile
from typing import List, Optional

from pdf2image import convert_from_bytes
from PIL import Image

from src.models.document import DocumentPage, FileType
from src.services.storage.s3_service import S3Service
from src.utils.exceptions import DonationProcessingError

logger = logging.getLogger(__name__)


class DocumentProcessingError(DonationProcessingError):
    """Exception raised for document processing errors."""

    pass


class DocumentProcessor:
    """Service for processing documents into images for AI extraction."""

    def __init__(self, s3_service: Optional[S3Service] = None):
        """
        Initialize document processor.

        Args:
            s3_service: S3 service instance for file storage
        """
        self.s3_service = s3_service
        self.max_image_size = (4096, 4096)  # Max size for Gemini API
        self.pdf_dpi = 200  # DPI for PDF conversion

    def process_document(
        self, file_content: bytes, file_type: FileType, file_id: str
    ) -> List[DocumentPage]:
        """
        Process a document into pages suitable for AI extraction.

        Args:
            file_content: Raw file content
            file_type: Type of the file
            file_id: Unique identifier for the file

        Returns:
            List of DocumentPage objects

        Raises:
            DocumentProcessingError: If processing fails
        """
        try:
            if file_type == FileType.PDF:
                return self._process_pdf(file_content, file_id)
            elif file_type in [FileType.JPEG, FileType.JPG, FileType.PNG]:
                return self._process_image(file_content, file_id)
            elif file_type == FileType.CSV:
                # CSV files don't need image conversion
                return self._process_csv(file_content, file_id)
            else:
                raise DocumentProcessingError(
                    f"Unsupported file type: {file_type}",
                    details={"file_type": file_type},
                )
        except Exception as e:
            logger.error(f"Failed to process document {file_id}: {e}")
            raise DocumentProcessingError(
                f"Failed to process document: {str(e)}",
                details={"file_id": file_id, "file_type": file_type},
            )

    def _process_pdf(self, pdf_content: bytes, file_id: str) -> List[DocumentPage]:
        """
        Process PDF document into individual page images.

        Args:
            pdf_content: PDF file content
            file_id: Unique identifier for the file

        Returns:
            List of DocumentPage objects
        """
        pages = []

        try:
            # Convert PDF to images
            images = convert_from_bytes(
                pdf_content,
                dpi=self.pdf_dpi,
                fmt="PNG",
                grayscale=False,
                size=self.max_image_size,
            )

            for i, image in enumerate(images):
                page_number = i + 1
                page_id = f"{file_id}_page_{page_number}"

                # Resize image if needed
                processed_image = self._resize_image(image)

                # Convert to bytes
                image_bytes = self._image_to_bytes(processed_image)

                # Create page object
                page = DocumentPage(
                    page_id=page_id,
                    file_id=file_id,
                    page_number=page_number,
                )

                # Store in S3 if service is available
                if self.s3_service:
                    s3_key = f"processed/{file_id}/page_{page_number}.png"
                    self.s3_service.upload_file(
                        image_bytes, s3_key, content_type="image/png"
                    )
                    page.s3_key = s3_key
                else:
                    # For testing or when S3 is not available
                    page.image_data = image_bytes.hex()

                pages.append(page)

            logger.info(f"Processed PDF {file_id} into {len(pages)} pages")
            return pages

        except Exception as e:
            raise DocumentProcessingError(
                f"Failed to process PDF: {str(e)}", details={"file_id": file_id}
            )

    def _process_image(self, image_content: bytes, file_id: str) -> List[DocumentPage]:
        """
        Process image document.

        Args:
            image_content: Image file content
            file_id: Unique identifier for the file

        Returns:
            List with single DocumentPage object
        """
        try:
            # Open image
            image = Image.open(io.BytesIO(image_content))

            # Convert to RGB if necessary
            if image.mode not in ("RGB", "RGBA"):
                image = image.convert("RGB")

            # Resize if needed
            processed_image = self._resize_image(image)

            # Convert to bytes
            image_bytes = self._image_to_bytes(processed_image)

            # Create page object
            page = DocumentPage(
                page_id=f"{file_id}_page_1",
                file_id=file_id,
                page_number=1,
            )

            # Store in S3 if service is available
            if self.s3_service:
                s3_key = f"processed/{file_id}/page_1.png"
                self.s3_service.upload_file(
                    image_bytes, s3_key, content_type="image/png"
                )
                page.s3_key = s3_key
            else:
                # For testing or when S3 is not available
                page.image_data = image_bytes.hex()

            logger.info(f"Processed image {file_id}")
            return [page]

        except Exception as e:
            raise DocumentProcessingError(
                f"Failed to process image: {str(e)}", details={"file_id": file_id}
            )

    def _process_csv(self, csv_content: bytes, file_id: str) -> List[DocumentPage]:
        """
        Process CSV document (no image conversion needed).

        Args:
            csv_content: CSV file content
            file_id: Unique identifier for the file

        Returns:
            List with single DocumentPage object containing CSV data
        """
        # CSV files are processed differently - no image conversion needed
        page = DocumentPage(
            page_id=f"{file_id}_page_1",
            file_id=file_id,
            page_number=1,
            # Store CSV content directly for processing
            extraction_result={
                "csv_content": csv_content.decode("utf-8", errors="ignore")
            },
        )

        logger.info(f"Processed CSV {file_id}")
        return [page]

    def _resize_image(self, image: Image.Image) -> Image.Image:
        """
        Resize image to fit within max dimensions while maintaining aspect ratio.

        Args:
            image: PIL Image object

        Returns:
            Resized image
        """
        if (
            image.size[0] <= self.max_image_size[0]
            and image.size[1] <= self.max_image_size[1]
        ):
            return image

        # Calculate new size maintaining aspect ratio
        ratio = min(
            self.max_image_size[0] / image.size[0],
            self.max_image_size[1] / image.size[1],
        )
        new_size = (int(image.size[0] * ratio), int(image.size[1] * ratio))

        return image.resize(new_size, Image.Resampling.LANCZOS)

    def _image_to_bytes(self, image: Image.Image) -> bytes:
        """
        Convert PIL Image to PNG bytes.

        Args:
            image: PIL Image object

        Returns:
            PNG image as bytes
        """
        buffer = io.BytesIO()
        image.save(buffer, format="PNG", optimize=True)
        return buffer.getvalue()

    def get_page_count(self, file_content: bytes, file_type: FileType) -> int:
        """
        Get the number of pages in a document.

        Args:
            file_content: Raw file content
            file_type: Type of the file

        Returns:
            Number of pages
        """
        try:
            if file_type == FileType.PDF:
                # Use a temporary file to count pages without full conversion
                with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp:
                    tmp.write(file_content)
                    tmp.flush()
                    from pdf2image import pdfinfo_from_path

                    info = pdfinfo_from_path(tmp.name)
                    return info.get("Pages", 1)
            else:
                # Single page for images and CSV
                return 1
        except Exception as e:
            logger.warning(f"Failed to get page count: {e}")
            return 1

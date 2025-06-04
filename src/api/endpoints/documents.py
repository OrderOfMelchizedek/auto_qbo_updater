"""Document upload and processing endpoints."""
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated, List, Optional

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from src.api.dependencies.auth import CurrentUser
from src.models.api import APIResponse, BatchUploadRequest
from src.models.document import (
    CompleteUploadRequest,
    FileType,
    FileUploadResponse,
    ProcessingStatus,
    ProcessingTask,
    UploadedFile,
)
from src.services.storage.s3_service import S3Service, S3StorageError
from src.utils.file_utils import validate_file_size, validate_file_type

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/documents", tags=["documents"])

# Initialize S3 service
s3_service = S3Service()


@router.post("/upload/prepare", response_model=APIResponse[FileUploadResponse])
async def prepare_upload(
    request: BatchUploadRequest,
    current_user: CurrentUser,
) -> APIResponse[FileUploadResponse]:
    """
    Get presigned URLs for uploading files.

    Returns URLs that can be used to upload files directly to S3.
    """
    try:
        batch_id = str(uuid.uuid4())
        upload_urls = {}
        file_ids = {}

        for filename in request.file_names:
            # Validate file type
            file_type = validate_file_type(filename)
            if not file_type:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unsupported file type for {filename}",
                )

            # Generate file ID and S3 key
            file_id = str(uuid.uuid4())
            user_id = current_user.get("sub")
            s3_key = f"uploads/{user_id}/{batch_id}/{file_id}/{filename}"

            # Get presigned upload URL
            upload_url = s3_service.generate_presigned_upload_url(
                s3_key, expires_in=3600
            )

            upload_urls[filename] = upload_url
            file_ids[filename] = file_id

        response = FileUploadResponse(
            upload_urls=upload_urls,
            file_ids=file_ids,
            batch_id=batch_id,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )

        return APIResponse(
            success=True,
            data=response,
            message="Upload URLs generated successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to prepare upload: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to prepare upload",
        )


@router.post("/upload/complete", response_model=APIResponse[List[UploadedFile]])
async def complete_upload(
    request: CompleteUploadRequest,
    current_user: CurrentUser,
) -> APIResponse[List[UploadedFile]]:
    """
    Confirm files were uploaded and store metadata.

    Call this after files have been uploaded to S3.
    """
    try:
        uploaded_files = []

        for file_info in request.file_metadata:
            # Verify file exists in S3
            s3_key = file_info["s3_key"]
            if not s3_service.file_exists(s3_key):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"File not found in storage: {file_info['filename']}",
                )

            # Get file info from S3
            file_size = s3_service.get_file_info(s3_key).get("ContentLength", 0)

            # Create uploaded file record
            uploaded_file = UploadedFile(
                file_id=file_info["file_id"],
                original_name=file_info["filename"],
                file_type=FileType(file_info["file_type"]),
                file_size=file_size,
                s3_key=s3_key,
                uploaded_by=current_user.get("sub", "unknown"),
            )
            uploaded_files.append(uploaded_file)

            # TODO: Store metadata in database

        # TODO: Update batch with uploaded files

        return APIResponse(
            success=True,
            data=uploaded_files,
            message=f"Uploaded {len(uploaded_files)} files successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to complete upload: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete upload",
        )


@router.post("/upload/direct", response_model=APIResponse[UploadedFile])
async def upload_file_direct(
    current_user: CurrentUser,
    file: Annotated[UploadFile, File()],
    batch_id: Optional[str] = None,
) -> APIResponse[UploadedFile]:
    """
    Upload a file directly through the API.

    Alternative to presigned URL upload for smaller files.
    """
    try:
        # Validate file
        if not file.filename or not validate_file_type(file.filename):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type: {file.filename}",
            )

        # Read file content
        content = await file.read()
        if not validate_file_size(len(content)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File size exceeds maximum allowed (20MB)",
            )

        # Generate IDs and S3 key
        file_id = str(uuid.uuid4())
        batch_id = batch_id or str(uuid.uuid4())
        user_id = current_user.get("sub")
        s3_key = f"uploads/{user_id}/{batch_id}/{file_id}/{file.filename}"

        # Upload to S3
        s3_service.upload_file(content, s3_key, content_type=file.content_type)

        # Create file record
        file_extension = file.filename.split(".")[-1].lower() if file.filename else ""
        uploaded_file = UploadedFile(
            file_id=file_id,
            original_name=file.filename or "unknown",
            file_type=FileType(file_extension),
            file_size=len(content),
            s3_key=s3_key,
            uploaded_by=current_user.get("sub", "unknown"),
        )

        # TODO: Store metadata in database

        return APIResponse(
            success=True,
            data=uploaded_file,
            message="File uploaded successfully",
        )
    except HTTPException:
        raise
    except S3StorageError as e:
        logger.error(f"S3 upload failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload file to storage",
        )
    except Exception as e:
        logger.error(f"Failed to upload file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload file",
        )


@router.get("/processing/{task_id}", response_model=APIResponse[ProcessingTask])
async def get_processing_status(
    task_id: str,
    current_user: CurrentUser,
) -> APIResponse[ProcessingTask]:
    """Get status of a document processing task."""
    try:
        # TODO: Get task status from Celery
        task = ProcessingTask(
            task_id=task_id,
            file_id="file_123",
            status=ProcessingStatus.PROCESSING,
        )

        return APIResponse(
            success=True,
            data=task,
            message="Task status retrieved",
        )
    except Exception as e:
        logger.error(f"Failed to get task status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get task status",
        )

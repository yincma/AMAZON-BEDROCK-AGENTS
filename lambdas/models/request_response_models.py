"""
Request and Response Models for Presentation Services
Common data models used across controllers and interfaces
"""

from typing import Optional
from pydantic import BaseModel, Field, validator


class CompileRequest(BaseModel):
    """Request model for PPTX compilation"""

    presentation_id: str = Field(
        ..., min_length=1, description="Presentation identifier"
    )
    session_id: Optional[str] = Field(default=None, description="Session identifier")
    template_id: Optional[str] = Field(default=None, description="Template to use")
    style: str = Field(default="professional", description="Presentation style")
    include_speaker_notes: bool = Field(
        default=True, description="Include speaker notes"
    )
    include_images: bool = Field(default=True, description="Include images")
    include_charts: bool = Field(default=True, description="Include charts")
    output_format: str = Field(default="pptx", description="Output format")

    @validator("style")
    def validate_style(cls, v):
        allowed_styles = ["professional", "creative", "minimalist", "technical"]
        if v not in allowed_styles:
            raise ValueError(f"Style must be one of: {', '.join(allowed_styles)}")
        return v

    @validator("output_format")
    def validate_format(cls, v):
        if v != "pptx":
            raise ValueError("Currently only 'pptx' format is supported")
        return v


class CompileResponse(BaseModel):
    """Response model for PPTX compilation"""

    success: bool
    presentation_id: str
    download_url: Optional[str] = None
    s3_key: Optional[str] = None
    file_size: int = 0
    slide_count: int = 0
    generation_time_ms: int = 0
    message: str
    error: Optional[str] = None

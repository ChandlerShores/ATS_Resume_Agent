"""Build sample_input.json format from parsed resume data."""

from typing import Dict, Any, Optional
from pathlib import Path

from ops.resume_parser import parse_resume
from ops.metrics_extractor import extract_metrics
from ops.parsing_errors import ValidationError as ParsingValidationError
from ops.logging import logger

# Import Pydantic model for validation
from schemas.models import JobInput
from pydantic import ValidationError as PydanticValidationError


def build_sample_input(
    resume_path: str,
    role: str,
    jd_text: Optional[str] = None,
    jd_url: Optional[str] = None,
    extra_context: Optional[str] = None,
    settings: Optional[Dict[str, Any]] = None,
    extract_metrics_flag: bool = True
) -> Dict[str, Any]:
    """
    Build JobInput-compatible dict from resume file.
    
    This function orchestrates the entire parsing pipeline:
    1. Parse resume file (DOCX/PDF/TXT)
    2. Extract bullets
    3. Extract metrics (optional)
    4. Build input dict
    5. Validate against JobInput Pydantic model
    
    Args:
        resume_path: Path to resume file
        role: Target role/position (required)
        jd_text: Job description text (optional)
        jd_url: Job description URL (optional)
        extra_context: Additional context about the role/candidate
        settings: Job settings (tone, max_len, variants)
        extract_metrics_flag: Whether to extract metrics (default True)
        
    Returns:
        Dict[str, Any]: Valid JobInput dict ready to save as JSON
        
    Raises:
        UnsupportedFormatError: If file format not supported
        FileReadError: If file cannot be read
        NoBulletsFoundError: If no bullets extracted
        ValidationError: If generated dict fails Pydantic validation
    """
    logger.info(
        stage="build_input",
        msg=f"Building input from {Path(resume_path).name}",
        role=role
    )
    
    # Parse resume
    parsed = parse_resume(resume_path)
    bullets = parsed['bullets']
    
    logger.info(
        stage="build_input",
        msg=f"Extracted {len(bullets)} bullets",
        file=Path(resume_path).name
    )
    
    # Extract metrics (non-critical)
    metrics = {}
    if extract_metrics_flag:
        try:
            metrics = extract_metrics(bullets)
            logger.info(
                stage="build_input",
                msg="Metrics extraction successful",
                metrics_count=sum([
                    len(metrics.get('percentages', [])),
                    len(metrics.get('dollar_amounts', [])),
                    len(metrics.get('counts', {})),
                    len(metrics.get('time_periods', []))
                ])
            )
        except Exception as e:
            logger.warn(
                stage="build_input",
                msg=f"Metrics extraction failed: {str(e)}"
            )
            metrics = {}
    
    # Build input dict
    input_dict = {
        "role": role,
        "bullets": bullets,
        "metrics": metrics,
    }
    
    # Add JD (required by state machine, use placeholder if not provided)
    if jd_url:
        input_dict["jd_url"] = jd_url
        input_dict["jd_text"] = None
    elif jd_text:
        input_dict["jd_text"] = jd_text
        input_dict["jd_url"] = None
    else:
        # Placeholder - user must replace before running state machine
        input_dict["jd_text"] = (
            "⚠️ JOB DESCRIPTION TO BE PROVIDED ⚠️\n\n"
            "Please replace this placeholder with the actual job description "
            "before running the state machine."
        )
        input_dict["jd_url"] = None
        logger.warn(
            stage="build_input",
            msg="No JD provided - using placeholder text"
        )
    
    # Add optional fields
    if extra_context:
        input_dict["extra_context"] = extra_context
    else:
        input_dict["extra_context"] = ""
    
    # Add settings with defaults
    if settings:
        input_dict["settings"] = settings
    else:
        input_dict["settings"] = {
            "tone": "concise",
            "max_len": 30,
            "variants": 2
        }
    
    # Validate against Pydantic model
    try:
        validated = JobInput(**input_dict)
        logger.info(
            stage="build_input",
            msg="Validation successful"
        )
        
        # Return as dict (Pydantic model validated but we return dict for JSON serialization)
        return input_dict
    
    except PydanticValidationError as e:
        error_details = str(e)
        logger.error(
            stage="build_input",
            msg=f"Pydantic validation failed: {error_details}"
        )
        raise ParsingValidationError(
            f"Generated input failed validation: {error_details}"
        )


def preview_extraction(resume_path: str, role: str) -> str:
    """
    Generate a preview of what would be extracted from a resume.
    
    Useful for CLI tools to show users what will be extracted before saving.
    
    Args:
        resume_path: Path to resume file
        role: Target role
        
    Returns:
        str: Human-readable preview
    """
    try:
        parsed = parse_resume(resume_path)
        bullets = parsed['bullets']
        metrics = extract_metrics(bullets)
        
        preview_lines = [
            f"Resume: {Path(resume_path).name}",
            f"Role: {role}",
            f"Format: {parsed['metadata']['format']}",
            "",
            f"Extracted {len(bullets)} bullets:",
            "---"
        ]
        
        for i, bullet in enumerate(bullets[:10], 1):  # Show first 10
            preview_lines.append(f"{i}. {bullet}")
        
        if len(bullets) > 10:
            preview_lines.append(f"... and {len(bullets) - 10} more")
        
        preview_lines.append("")
        preview_lines.append("Extracted metrics:")
        preview_lines.append("---")
        
        if metrics:
            if metrics.get('percentages'):
                preview_lines.append(f"Percentages: {', '.join(metrics['percentages'])}")
            if metrics.get('dollar_amounts'):
                preview_lines.append(f"Dollar amounts: {', '.join(metrics['dollar_amounts'])}")
            if metrics.get('counts'):
                count_strs = [f"{v} {k}" for k, v in metrics['counts'].items()]
                preview_lines.append(f"Counts: {', '.join(count_strs)}")
            if metrics.get('time_periods'):
                preview_lines.append(f"Time periods: {', '.join(metrics['time_periods'])}")
        else:
            preview_lines.append("(No metrics found)")
        
        return '\n'.join(preview_lines)
    
    except Exception as e:
        return f"Error generating preview: {str(e)}"


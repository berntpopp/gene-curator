"""
Backend Sanitization Module for Gene Curator

Fixes Issue #8: Provides privacy protection for sensitive data in backend logs.
This mirrors the frontend sanitization but for Python backend.
"""

import re
from typing import Any

# Sensitive keys that should be redacted from logs
SENSITIVE_KEYS = {
    # Authentication and security
    "token",
    "accesstoken",
    "authtoken",
    "jwt",
    "password",
    "passwd",
    "pwd",
    "key",
    "apikey",
    "api_key",
    "secretkey",
    "secret_key",
    "privatekey",
    "private_key",
    "secret",
    "apisecret",
    "api_secret",
    "authorization",
    "bearer",
    "credential",
    "credentials",
    # User identifiers (if needed for privacy)
    "email",
    "emailaddress",
    "phone",
    "phonenumber",
    # Genetic data (optional - depends on privacy requirements)
    "variant",
    "variants",
    "mutation",
    "mutations",
    "hgvs",
    "hgvs_notation",
}

# Regex patterns for sensitive values
SENSITIVE_VALUE_PATTERNS = [
    # Email patterns
    (
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
        "[REDACTED_EMAIL]",
    ),
    # JWT token patterns
    (
        re.compile(r"\b[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\b"),
        "[REDACTED_TOKEN]",
    ),
    # API key patterns (32+ alphanumeric)
    (re.compile(r"\b[A-Za-z0-9]{32,}\b"), "[REDACTED_KEY]"),
    # HGVS notation for genetic variants (DNA)
    (re.compile(r"\bc\.\d+[ACGT]>[ACGT]\b"), "[REDACTED_VARIANT]"),
    (re.compile(r"\bc\.\d+_\d+del[ACGT]*\b"), "[REDACTED_VARIANT]"),
    (re.compile(r"\bc\.\d+_\d+ins[ACGT]+\b"), "[REDACTED_VARIANT]"),
    # HGVS notation for genetic variants (Protein)
    (re.compile(r"\bp\.[A-Z][a-z]{2}\d+[A-Z][a-z]{2}\b"), "[REDACTED_VARIANT]"),
    (re.compile(r"\bp\.[A-Z][a-z]{2}\d+\*"), "[REDACTED_VARIANT]"),
    # Genomic coordinates
    (re.compile(r"\bchr\d{1,2}:\d+-\d+\b"), "[REDACTED_COORDINATE]"),
]


def sanitize_dict(data: dict[str, Any] | None, max_depth: int = 5) -> dict[str, Any]:
    """
    Sanitize sensitive data from dictionary.

    Args:
        data: Dictionary to sanitize
        max_depth: Maximum recursion depth

    Returns:
        Sanitized copy of the dictionary
    """
    if data is None:
        return {}

    if max_depth <= 0:
        return {"_truncated": "MAX_DEPTH_EXCEEDED"}

    sanitized: dict[str, Any] = {}

    for key, value in data.items():
        # Normalize key for comparison
        key_lower = key.lower().replace("_", "").replace("-", "")

        # Check if key is sensitive
        if any(pattern in key_lower for pattern in SENSITIVE_KEYS):
            sanitized[key] = "[REDACTED]"
        elif isinstance(value, dict):
            sanitized[key] = sanitize_dict(value, max_depth - 1)
        elif isinstance(value, list):
            sanitized[key] = [
                sanitize_dict(v, max_depth - 1)
                if isinstance(v, dict)
                else sanitize_value(v)
                for v in value[:100]  # Limit array size
            ]
        else:
            sanitized[key] = sanitize_value(value)

    return sanitized


def sanitize_value(value: Any) -> Any:
    """
    Sanitize primitive values by checking against sensitive patterns.

    Args:
        value: Value to sanitize

    Returns:
        Sanitized value
    """
    if not isinstance(value, str):
        return value

    # Quick check: if no special chars, skip regex tests (performance optimization)
    if not re.search(r"[@.:+-]", value):
        return value

    sanitized = value

    # Apply regex patterns to detect and redact sensitive values
    for pattern, replacement in SENSITIVE_VALUE_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)

    return sanitized


def sanitize_for_logging(obj: Any, max_depth: int = 5) -> Any:
    """
    Sanitizes an object for logging by redacting sensitive information.

    Args:
        obj: The object to sanitize
        max_depth: Maximum recursion depth

    Returns:
        Sanitized copy of the object
    """
    if obj is None:
        return None

    if max_depth <= 0:
        return "[MAX_DEPTH_EXCEEDED]"

    # Handle primitives
    if isinstance(obj, str | int | float | bool):
        return sanitize_value(obj)

    # Handle dictionaries
    if isinstance(obj, dict):
        return sanitize_dict(obj, max_depth)

    # Handle lists
    if isinstance(obj, list):
        return [sanitize_for_logging(item, max_depth - 1) for item in obj[:100]]

    # For other types, convert to string and sanitize
    return sanitize_value(str(obj))

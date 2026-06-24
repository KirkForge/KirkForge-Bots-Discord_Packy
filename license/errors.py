"""License-related exceptions.

The boot gate distinguishes these so the error message can tell the user
exactly what to fix (missing file vs wrong tier vs expired vs bad signature).
"""

from __future__ import annotations


class LicenseError(Exception):
    """Base class for license problems. The product refuses to boot."""


class LicenseNotFoundError(LicenseError):
    """No license file found at any of the search paths."""


class LicenseFormatError(LicenseError):
    """License file is unreadable (bad JSON, missing required fields)."""


class LicenseSignatureError(LicenseError):
    """Signature did not verify. License is forged, tampered, or signed by an
    old key the product no longer trusts."""


class LicenseExpiredError(LicenseError):
    """Support contract is expired. The product still boots in read-only mode
    for tier features that don't require support; tier-locked features refuse."""


class LicenseFeatureUnavailable(LicenseError):
    """Customer's tier does not include the requested feature. Not fatal at
    boot — only raised when a specific feature is accessed."""


class LicenseProductMismatchError(LicenseError):
    """The signed license is valid but for a different product (e.g. a
    The Specialist license used to boot Gargoyle Packy). Reject before any
    claim value is consulted."""


class LicenseTamperError(LicenseError):
    """Detected a modification to the license file, key, or boot path that
    looks like a tamper attempt. Refuses to boot and asks the user to
    reinstall from a clean source."""

"""Input validation for image-based entry points."""

from __future__ import annotations

from pathlib import Path


class ImageValidationError(ValueError):
    """Raised when an uploaded or local image is not acceptable."""


_ALLOWED_SUFFIXES = {".png", ".jpg", ".jpeg"}
_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
_JPEG_MAGIC = b"\xff\xd8\xff"


def validate_image_path(path: str | Path, *, max_size_bytes: int) -> Path:
    image_path = Path(path)
    if not image_path.is_file():
        raise ImageValidationError(f"image not found: {image_path}")
    if image_path.suffix.lower() not in _ALLOWED_SUFFIXES:
        raise ImageValidationError("only PNG and JPEG images are accepted")
    size = image_path.stat().st_size
    if size <= 0:
        raise ImageValidationError("image is empty")
    if size > max_size_bytes:
        raise ImageValidationError("image exceeds configured size limit")
    with image_path.open("rb") as handle:
        header = handle.read(8)
    if image_path.suffix.lower() == ".png" and not header.startswith(_PNG_MAGIC):
        raise ImageValidationError("file extension is PNG but bytes are not PNG")
    if image_path.suffix.lower() in {".jpg", ".jpeg"} and not header.startswith(_JPEG_MAGIC):
        raise ImageValidationError("file extension is JPEG but bytes are not JPEG")
    return image_path


def media_type_for_path(path: str | Path) -> str:
    suffix = Path(path).suffix.lower()
    if suffix == ".png":
        return "image/png"
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    raise ImageValidationError("only PNG and JPEG images are accepted")

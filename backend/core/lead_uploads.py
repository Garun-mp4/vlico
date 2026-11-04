from hashlib import sha256
from io import BytesIO
from pathlib import PurePosixPath
import warnings
from django.core.exceptions import ValidationError
from PIL import Image, ImageOps, UnidentifiedImageError
from pypdf import PdfReader
from pypdf.errors import PdfReadError

MAX_FILE_SIZE = 8 * 1024 * 1024
MAX_FILES = 3


def prepare_attachments(files):
    if len(files) > MAX_FILES:
        raise ValidationError("Можно приложить до трёх файлов.")
    prepared = []
    for file in files:
        if file.size > MAX_FILE_SIZE:
            raise ValidationError("Каждый файл должен быть не больше 8 МБ.")
        name = PurePosixPath(file.name.replace("\\", "/")).name[:180]
        name = "".join(char if ord(char) >= 32 else "_" for char in name)
        suffix = PurePosixPath(name).suffix.lower()
        data = file.read(MAX_FILE_SIZE + 1)
        if not data or len(data) > MAX_FILE_SIZE:
            raise ValidationError("Файл пуст или превышает 8 МБ.")
        digest = sha256(data).hexdigest()
        if suffix == ".pdf":
            try:
                if not data.startswith(b"%PDF-") or b"%%EOF" not in data[-1024:]:
                    raise ValueError
                reader = PdfReader(BytesIO(data), strict=True)
                if reader.is_encrypted or not 1 <= len(reader.pages) <= 100:
                    raise ValueError
                root = reader.trailer["/Root"]
                if any(key in root for key in ("/OpenAction", "/AA")) or "/EmbeddedFiles" in root.get("/Names", {}):
                    raise ValueError
            except (PdfReadError, ValueError, TypeError, KeyError, RecursionError, OSError):
                raise ValidationError("Не удалось проверить PDF. Выберите обычный PDF до 100 страниц, без пароля и вложенных файлов.")
            content_type = "application/pdf"
        elif suffix in {".jpg", ".jpeg", ".png", ".webp"}:
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("error", Image.DecompressionBombWarning)
                    with Image.open(BytesIO(data)) as source:
                        if source.format not in {"JPEG", "PNG", "WEBP"} or source.width * source.height > 16_000_000 or min(source.size) < 64:
                            raise ValueError
                        source.load()
                        image = ImageOps.exif_transpose(source).convert("RGB")
                        image.thumbnail((4000, 4000))
                        output = BytesIO()
                        image.save(output, "WEBP", quality=90)
                        data = output.getvalue()
                        if len(data) > MAX_FILE_SIZE:
                            raise ValueError
            except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning):
                raise ValidationError("Не удалось проверить изображение. Допустимы JPEG, PNG и WebP от 64 пикселей до 16 мегапикселей.")
            name = PurePosixPath(name).stem + ".webp"
            suffix, content_type = ".webp", "image/webp"
        else:
            raise ValidationError("Допустимы только PDF, JPEG, PNG и WebP.")
        prepared.append({"name": name, "suffix": suffix, "content_type": content_type, "data": data, "digest": digest})
    return prepared

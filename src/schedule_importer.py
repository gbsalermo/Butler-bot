import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from src.sigaa_schedule import parse_sigaa_schedule


@dataclass
class ImportedSubject:
    name: str
    code: str
    location: str
    sessions: list[tuple[str, str, str, str]] = field(default_factory=list)


_CODE_RE = re.compile(r"(?<![A-Z0-9])([2-7]{1,6})\s*([MTN])\s*([1-6]{1,6})(?![A-Z0-9])", re.I)
_DAY_WORDS = r"(?:SEG|TER|QUA|QUI|SEX|SAB|SÁB)"
_LOCATION_MARKERS = re.compile(r"\b(PAV(?:ILH[AÃ]O)?|BLOCO|SALA|LAB(?:ORAT[ÓO]RIO)?|AUDIT[ÓO]RIO|PR[ÉE]DIO|CAMPUS)\b", re.I)


def extract_text_from_file(path: str | Path) -> str:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _extract_pdf(path)
    return _ocr_image(path)


def _extract_pdf(path: Path) -> str:
    try:
        import fitz
    except ImportError as exc:
        raise RuntimeError("PyMuPDF não instalado. Rode pip install -r requirements.txt.") from exc

    doc = fitz.open(path)
    text = "\n".join(page.get_text("text") for page in doc).strip()
    if len(text) >= 40 and _CODE_RE.search(text):
        return text

    # PDF escaneado: renderiza páginas e usa o mesmo OCR das imagens.
    chunks: list[str] = []
    for index, page in enumerate(doc):
        pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0), alpha=False)
        with tempfile.NamedTemporaryFile(suffix=f"-{index}.png", delete=False) as tmp:
            image_path = Path(tmp.name)
        try:
            pix.save(str(image_path))
            chunks.append(_ocr_image(image_path))
        finally:
            image_path.unlink(missing_ok=True)
    return "\n".join(chunks)


def _ocr_image(path: Path) -> str:
    try:
        import pytesseract
        from PIL import Image, ImageEnhance, ImageOps
    except ImportError as exc:
        raise RuntimeError("OCR não instalado. Rode pip install -r requirements.txt.") from exc

    try:
        image = Image.open(path).convert("L")
        image = ImageOps.autocontrast(image)
        image = ImageEnhance.Contrast(image).enhance(1.4)
        return pytesseract.image_to_string(image, lang="por+eng", config="--psm 6")
    except pytesseract.TesseractNotFoundError as exc:
        raise RuntimeError(
            "O Tesseract OCR não foi encontrado no computador. Instale o Tesseract para importar imagens/PDFs escaneados."
        ) from exc


def parse_schedule_text(text: str) -> list[ImportedSubject]:
    lines = [_clean_line(line) for line in text.splitlines() if _clean_line(line)]
    found: list[ImportedSubject] = []

    for i, line in enumerate(lines):
        match = _CODE_RE.search(line)
        if not match:
            continue

        code = "".join(match.groups()).upper()
        prefix = line[: match.start()].strip(" -|:")
        subject, location = _subject_location(prefix)

        # OCR frequentemente joga nome/local para a linha imediatamente anterior.
        if not subject and i > 0:
            previous = lines[i - 1]
            subject, location = _subject_location(f"{previous} {prefix}".strip())
        elif subject and not location and i > 0 and len(subject.split()) <= 2:
            p_subject, p_location = _subject_location(f"{lines[i - 1]} {prefix}".strip())
            subject, location = p_subject or subject, p_location or location

        if not subject:
            continue

        try:
            parsed = parse_sigaa_schedule(code)
        except ValueError:
            continue

        location = _clean_location(location)
        sessions = [(day, parsed.start_time, parsed.end_time, _location_for_day(location, day)) for day in parsed.weekdays]
        found.append(ImportedSubject(name=_title_subject(subject), code=code, location=location, sessions=sessions))

    return _merge_duplicates(found)


def _clean_line(value: str) -> str:
    value = value.replace("|", " ")
    return " ".join(value.split())


def _subject_location(prefix: str) -> tuple[str, str]:
    prefix = re.sub(r"^(COMPONENTE CURRICULAR|LOCAL|HOR[ÁA]RIO|CHAT)\s*", "", prefix, flags=re.I).strip()
    marker = _LOCATION_MARKERS.search(prefix)
    if marker:
        subject = prefix[: marker.start()].strip(" -,:;")
        location = prefix[marker.start():].strip()
        return subject, location

    # Em texto extraído de tabela, colunas podem vir separadas por vários espaços.
    pieces = [p.strip() for p in re.split(r"\s{2,}", prefix) if p.strip()]
    if len(pieces) >= 2:
        return pieces[0], " ".join(pieces[1:])
    return prefix.strip(), ""


def _clean_location(location: str) -> str:
    location = re.sub(r"\s+", " ", location).strip(" -,:;")
    # Mantém anotações SEG/QUA quando descrevem salas diferentes; remove apenas finais simples.
    simple_days = re.compile(rf"\s+(?:{_DAY_WORDS})(?:\s+E\s+{_DAY_WORDS})+$", re.I)
    return simple_days.sub("", location).strip()


def _location_for_day(location: str, weekday: str) -> str:
    # Caso comum do SIGAA: "PAV I, SALA 11 SEG E SALA 114 QUA".
    short = {
        "segunda-feira": "SEG", "terça-feira": "TER", "quarta-feira": "QUA",
        "quinta-feira": "QUI", "sexta-feira": "SEX", "sábado": "SAB",
    }.get(weekday)
    if not short or not location:
        return location

    base_match = re.match(r"^(.*?)(SALA\s+[^,;]+?\s+(?:SEG|TER|QUA|QUI|SEX|SAB)\b.*)$", location, re.I)
    if not base_match:
        return location
    base, tail = base_match.groups()
    for room, day in re.findall(r"SALA\s+([^,;]+?)\s+(SEG|TER|QUA|QUI|SEX|SAB)\b", tail, re.I):
        if day.upper() == short:
            return f"{base.strip(' ,;-')} Sala {room.strip()}".strip()
    return location


def _title_subject(value: str) -> str:
    value = re.sub(r"\s+", " ", value).strip(" -,:;")
    # Se OCR já veio todo em maiúsculo, Title preserva números/romanos razoavelmente bem.
    if value.isupper():
        small = {"de", "da", "do", "das", "dos", "e", "para"}
        words = []
        for index, word in enumerate(value.lower().split()):
            words.append(word if index and word in small else word.capitalize())
        return " ".join(words).replace(" Ii", " II").replace(" Iii", " III").replace(" Iv", " IV")
    return value


def _merge_duplicates(items: list[ImportedSubject]) -> list[ImportedSubject]:
    merged: dict[str, ImportedSubject] = {}
    for item in items:
        key = item.name.casefold()
        if key not in merged:
            merged[key] = item
            continue
        current = merged[key]
        existing = set(current.sessions)
        for session in item.sessions:
            if session not in existing:
                current.sessions.append(session)
    return list(merged.values())

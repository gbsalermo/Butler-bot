import re
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
_DAY_ONLY_RE = re.compile(rf"^(?:{_DAY_WORDS})(?:\s+E\s+(?:{_DAY_WORDS}))*$", re.I)
_LOCATION_MARKERS = re.compile(r"\b(PAV(?:ILH[AÃ]O)?|BLOCO|SALA|LAB(?:ORAT[ÓO]RIO)?|AUDIT[ÓO]RIO|PR[ÉE]DIO|CAMPUS)\b", re.I)
_HEADERS = {
    "componente curricular",
    "local",
    "horário",
    "horario",
    "chat",
    "grade de componentes curriculares",
}


def extract_text_from_file(path: str | Path) -> str:
    path = Path(path)
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        return _extract_pdf_text(path)
    if suffix == ".txt":
        return _extract_txt(path)

    raise ValueError("Formato não aceito. Envie um PDF com texto pesquisável ou um arquivo .txt.")


def _extract_pdf_text(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("pypdf não instalado. Rode pip install -r requirements.txt.") from exc

    reader = PdfReader(str(path))
    text = "\n".join((page.extract_text() or "") for page in reader.pages).strip()

    if len(text) < 20:
        raise RuntimeError(
            "Este PDF não possui texto pesquisável suficiente. Se ele veio de uma imagem ou scan, converta antes para PDF com texto."
        )

    return text


def _extract_txt(path: Path) -> str:
    raw = path.read_bytes()
    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            text = raw.decode(encoding).strip()
            if text:
                return text
        except UnicodeDecodeError:
            continue
    raise RuntimeError("Não consegui ler o arquivo de texto.")


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

        if not subject or _looks_like_day_text(subject):
            context_subject, context_location = _context_before_code(lines, i)
            subject = context_subject or subject
            location = context_location or location

        if not subject or _looks_like_day_text(subject):
            continue

        try:
            parsed = parse_sigaa_schedule(code)
        except ValueError:
            continue

        location = _clean_location(location)
        sessions = [
            (day, parsed.start_time, parsed.end_time, _location_for_day(location, day))
            for day in parsed.weekdays
        ]
        found.append(
            ImportedSubject(
                name=_title_subject(subject),
                code=code,
                location=location,
                sessions=sessions,
            )
        )

    return _merge_duplicates(found)


def _context_before_code(lines: list[str], code_index: int) -> tuple[str, str]:
    """Lê tabelas cujo PDF extrai nome, local, dias e código em linhas separadas."""
    location_parts: list[str] = []
    subject = ""

    for j in range(code_index - 1, max(-1, code_index - 6), -1):
        line = lines[j].strip()
        lowered = line.casefold()

        if lowered in _HEADERS or lowered.startswith("ufrb —") or lowered.startswith("ufrb -"):
            continue
        if _looks_like_day_text(line):
            continue
        if _looks_like_location(line):
            location_parts.insert(0, line)
            continue
        if _CODE_RE.search(line):
            break

        subject = line
        break

    return subject, " ".join(location_parts)


def _looks_like_day_text(value: str) -> bool:
    return bool(_DAY_ONLY_RE.fullmatch(value.strip()))


def _looks_like_location(value: str) -> bool:
    cleaned = value.strip()
    return bool(_LOCATION_MARKERS.search(cleaned) or re.match(r"^E\s+SALA\b", cleaned, re.I))


def _clean_line(value: str) -> str:
    return " ".join(value.replace("|", " ").split())


def _subject_location(prefix: str) -> tuple[str, str]:
    prefix = re.sub(
        r"^(COMPONENTE CURRICULAR|LOCAL|HOR[ÁA]RIO|CHAT)\s*",
        "",
        prefix,
        flags=re.I,
    ).strip()

    marker = _LOCATION_MARKERS.search(prefix)
    if marker:
        return (
            prefix[: marker.start()].strip(" -,:;"),
            prefix[marker.start():].strip(),
        )

    pieces = [piece.strip() for piece in re.split(r"\s{2,}", prefix) if piece.strip()]
    if len(pieces) >= 2:
        return pieces[0], " ".join(pieces[1:])
    return prefix.strip(), ""


def _clean_location(location: str) -> str:
    location = re.sub(r"\s+", " ", location).strip(" -,:;")
    simple_days = re.compile(rf"\s+(?:{_DAY_WORDS})(?:\s+E\s+{_DAY_WORDS})+$", re.I)
    return simple_days.sub("", location).strip()


def _location_for_day(location: str, weekday: str) -> str:
    short = {
        "segunda-feira": "SEG",
        "terça-feira": "TER",
        "quarta-feira": "QUA",
        "quinta-feira": "QUI",
        "sexta-feira": "SEX",
        "sábado": "SAB",
    }.get(weekday)
    if not short or not location:
        return location

    base_match = re.match(
        r"^(.*?)(SALA\s+[^,;]+?\s+(?:SEG|TER|QUA|QUI|SEX|SAB)\b.*)$",
        location,
        re.I,
    )
    if not base_match:
        return location

    base, tail = base_match.groups()
    for room, day in re.findall(
        r"SALA\s+([^,;]+?)\s+(SEG|TER|QUA|QUI|SEX|SAB)\b",
        tail,
        re.I,
    ):
        if day.upper() == short:
            return f"{base.strip(' ,;-')} Sala {room.strip()}".strip()
    return location


def _title_subject(value: str) -> str:
    value = re.sub(r"\s+", " ", value).strip(" -,:;")
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

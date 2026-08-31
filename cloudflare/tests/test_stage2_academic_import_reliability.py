import asyncio
import inspect
import sqlite3

import academic_import
import performance_patch


class Statement:
    def __init__(self, conn, sql):
        self.conn = conn
        self.sql = sql
        self.params = ()

    def bind(self, *params):
        self.params = params
        return self

    async def first(self):
        cur = self.conn.execute(self.sql, self.params)
        return cur.fetchone()

    async def run(self):
        self.conn.execute(self.sql, self.params)
        self.conn.commit()
        return None


class FakeD1:
    def __init__(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(
            """
            PRAGMA foreign_keys=ON;
            CREATE TABLE subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                UNIQUE(user_id,name)
            );
            CREATE TABLE subject_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_id INTEGER NOT NULL,
                weekday TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                location TEXT,
                FOREIGN KEY(subject_id) REFERENCES subjects(id) ON DELETE CASCADE
            );
            """
        )

    def prepare(self, sql):
        return Statement(self.conn, sql)


def test_same_line_sigaa_record_preserves_current_model():
    report = academic_import.parse_schedule_report(
        "Sistemas Digitais I 35M45 PAV II sala 05"
    )
    assert report["confidence"] == "high"
    assert report["issues"] == []
    assert report["subject_count"] == 1
    assert report["session_count"] == 2
    assert [(x["weekday"], x["start"], x["end"]) for x in report["items"]] == [
        ("terça-feira", "10:00", "12:00"),
        ("quinta-feira", "10:00", "12:00"),
    ]
    assert all(x["location"] == "PAV II sala 05" for x in report["items"])


def test_wrapped_pdf_columns_are_reconstructed():
    text = """
    Componente Curricular
    Cálculo Numérico
    PAV III, Sala 10
    24M23
    """
    report = academic_import.parse_schedule_report(text)
    assert report["confidence"] == "high"
    assert report["subject_count"] == 1
    assert report["session_count"] == 2
    assert {x["weekday"] for x in report["items"]} == {"segunda-feira", "quarta-feira"}
    assert all(x["start"] == "08:00" and x["end"] == "10:00" for x in report["items"])
    assert all(x["location"] == "PAV III, Sala 10" for x in report["items"])


def test_location_after_schedule_is_attached_without_creating_fake_subject():
    report = academic_import.parse_schedule_report(
        "Algoritmos 2T23\nLaboratório 04"
    )
    assert report["confidence"] == "high"
    assert report["subject_count"] == 1
    assert report["session_count"] == 1
    assert report["items"][0]["location"] == "Laboratório 04"


def test_wrapped_subject_name_is_joined():
    report = academic_import.parse_schedule_report(
        "Introdução à\nProgramação 2M12 Sala 01"
    )
    assert report["confidence"] == "high"
    assert report["items"][0]["name"] == "Introdução à Programação"


def test_duplicate_pdf_rows_do_not_duplicate_sessions():
    text = """
    Física I 35M45 PAV I
    Física I 35M45 PAV I
    """
    report = academic_import.parse_schedule_report(text)
    assert report["confidence"] == "high"
    assert report["subject_count"] == 1
    assert report["session_count"] == 2


def test_multiple_schedule_codes_on_one_record_are_supported():
    report = academic_import.parse_schedule_report(
        "Projeto Integrador 2M12 5T34 Sala Maker"
    )
    assert report["confidence"] == "high"
    assert report["session_count"] == 2
    assert {(x["weekday"], x["start"], x["end"]) for x in report["items"]} == {
        ("segunda-feira", "07:00", "09:00"),
        ("quinta-feira", "15:00", "17:00"),
    }


def test_missing_location_is_valid_because_current_model_allows_it():
    report = academic_import.parse_schedule_report("Álgebra Linear 2M12")
    assert report["confidence"] == "high"
    assert report["issues"] == []
    assert report["items"][0]["location"] is None


def test_invalid_or_ambiguous_sigaa_code_blocks_entire_first_import():
    report = academic_import.parse_schedule_report(
        "Cálculo I 35M45 PAV I\nFísica I 24M29 PAV II"
    )
    assert report["confidence"] == "medium"
    assert report["items"]
    assert report["issues"]
    assert "inválido" in report["issues"][0]["reason"]


def test_non_contiguous_slots_are_not_silently_stretched():
    report = academic_import.parse_schedule_report("Cálculo I 2M24 PAV I")
    assert report["confidence"] == "low"
    assert report["items"] == []
    assert any("não contíguos" in x["reason"] for x in report["issues"])


def test_free_text_is_not_invented_as_schedule():
    report = academic_import.parse_schedule_report(
        "Lembrete: revisar cálculo amanhã e procurar a sala depois"
    )
    assert report["confidence"] == "low"
    assert report["items"] == []


def test_repeated_sigaa_headers_and_page_noise_are_ignored():
    text = """
    SIGAA
    Componente Curricular
    Local
    Horário
    Redes de Computadores 6M12 LAB 2
    Página 1 de 2
    Universidade Federal do Recôncavo
    """
    report = academic_import.parse_schedule_report(text)
    assert report["confidence"] == "high"
    assert report["subject_count"] == 1
    assert report["session_count"] == 1


def test_preview_distinguishes_safe_from_review_required():
    clean = academic_import.parse_schedule_report("Cálculo I 2M12 Sala 01")
    clean_text = academic_import.preview_text(clean)
    assert "Tudo bateu" in clean_text
    assert "Cálculo I" in clean_text

    mixed = academic_import.parse_schedule_report(
        "Cálculo I 2M12 Sala 01\nFísica I 2M29 Sala 02"
    )
    mixed_text = academic_import.preview_text(mixed)
    assert "Não vou cadastrar ainda" in mixed_text
    assert "Nada foi salvo" in mixed_text


def test_first_import_persists_into_existing_subject_tables_only():
    async def scenario():
        db = FakeD1()
        report = academic_import.parse_schedule_report(
            "Cálculo I 35M45 PAV I\nFísica I 2T23 LAB 3"
        )
        subjects, sessions = await academic_import._persist_first_import(db, 10, report["items"])
        assert subjects == 2
        assert sessions == 3

        subject_rows = db.conn.execute(
            "SELECT user_id,name,active FROM subjects ORDER BY name"
        ).fetchall()
        session_rows = db.conn.execute(
            "SELECT weekday,start_time,end_time,location FROM subject_sessions ORDER BY id"
        ).fetchall()
        assert len(subject_rows) == 2
        assert all(row["user_id"] == 10 and row["active"] == 1 for row in subject_rows)
        assert len(session_rows) == 3

    asyncio.run(scenario())


def test_runtime_bootstrap_installs_academic_import_without_schema_change():
    source = inspect.getsource(performance_patch.install_performance_patches)
    assert "academic_import.install()" in source
    module_source = inspect.getsource(academic_import)
    assert "ALTER TABLE" not in module_source
    assert "CREATE TABLE" not in module_source
    assert "INSERT INTO subjects" in module_source
    assert "INSERT INTO subject_sessions" in module_source

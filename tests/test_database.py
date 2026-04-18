import app.database as db


def test_get_pending_returns_empty_initially():
    assert db.get_pending() == []


def test_insert_transcription_creates_pending_record():
    db.insert_transcription(file_path="/audio/aula01.mp3", text="Olá mundo")

    pending = db.get_pending()

    assert len(pending) == 1
    assert pending[0]["file_path"] == "/audio/aula01.mp3"
    assert pending[0]["text"] == "Olá mundo"
    assert pending[0]["status"] == "pending"


def test_insert_transcription_upsert_resets_status_to_pending():
    db.insert_transcription(file_path="/audio/aula01.mp3", text="first")
    row_id = db.get_pending()[0]["id"]
    db.set_status(row_id, "sent")

    db.insert_transcription(file_path="/audio/aula01.mp3", text="updated")

    pending = db.get_pending()
    assert len(pending) == 1
    assert pending[0]["text"] == "first"
    assert pending[0]["status"] == "pending"


def test_set_status_changes_record_status():
    db.insert_transcription(file_path="/audio/aula01.mp3", text="hello")
    row_id = db.get_pending()[0]["id"]

    db.set_status(row_id, "sent")

    assert db.get_pending() == []
    row = db.get_transcription(row_id)
    assert row["status"] == "sent"


def test_has_segments_returns_false_when_missing():
    db.insert_transcription(file_path="/audio/aula01.mp3", text="hello")

    assert db.has_segments("/audio/aula01.mp3") is False


def test_has_segments_returns_true_when_present():
    db.insert_transcription(
        file_path="/audio/aula01.mp3", text="hello", segments_json='[{"start":0}]'
    )

    assert db.has_segments("/audio/aula01.mp3") is True


def test_get_unsummarized_excludes_records_with_summary():
    db.insert_transcription(file_path="/audio/aula01.mp3", text="first")
    db.insert_transcription(file_path="/audio/aula02.mp3", text="second")
    row_id = db.get_all_transcriptions()[0]["id"]
    db.set_summary(row_id, "my summary")

    unsummarized = db.get_unsummarized()

    assert len(unsummarized) == 1
    assert unsummarized[0]["file_path"] == "/audio/aula02.mp3"


def test_set_summary_stores_text():
    db.insert_transcription(file_path="/audio/aula01.mp3", text="hello")
    row_id = db.get_pending()[0]["id"]

    db.set_summary(row_id, "This class covered neural networks.")

    row = db.get_transcription(row_id)
    assert row["summary"] == "This class covered neural networks."


def test_get_transcription_returns_none_for_missing_id():
    assert db.get_transcription(999) is None

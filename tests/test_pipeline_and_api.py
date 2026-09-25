from fastapi.testclient import TestClient

from docint.api.main import app
from docint.pipeline import process_document
from docint.schemas import DocumentResult, DocType


def test_pipeline_returns_valid_contract():
    result = process_document(b"fake", "invoice.png")
    assert isinstance(result, DocumentResult)
    assert result.doc_type == DocType.invoice
    assert "total" in result.fields
    assert all(v.passed for v in result.validation)


def test_api_upload_get_search():
    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok"}
        r = client.post("/documents", files={"file": ("inv.png", b"fake", "image/png")})
        assert r.status_code == 200
        doc_id = r.json()["doc_id"]
        assert client.get(f"/documents/{doc_id}").json()["doc_type"] == "invoice"
        assert len(client.get("/search", params={"doc_type": "invoice"}).json()) >= 1
        assert client.get("/documents/nope").status_code == 404

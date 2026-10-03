"""OWNER: Person D  |  Branch: feature/ui-review

Smart Document & Form Intelligence System — Human Review UI
============================================================

Run with:
    streamlit run src/docint/ui/app.py

Configuration (environment variables):
    API_URL   URL of the FastAPI backend  (default: http://localhost:8000)
"""
from __future__ import annotations

import io
import os
from typing import Any, Optional

import requests
import streamlit as st

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
API_URL = os.getenv("API_URL", "http://localhost:8000").rstrip("/")

LOW_CONF_THRESHOLD = 0.6

st.set_page_config(
    page_title="DocSense Review UI",
    page_icon="📄",
    layout="wide",
)

# ---------------------------------------------------------------------------
# API helpers – all errors are surfaced via st.error, no tracebacks shown
# ---------------------------------------------------------------------------

def _get(path: str, params: dict | None = None) -> Optional[Any]:
    try:
        r = requests.get(f"{API_URL}{path}", params=params, timeout=15)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        st.error(f"Cannot connect to API at {API_URL}. Is the server running?")
    except requests.exceptions.HTTPError as e:
        st.error(f"API error {e.response.status_code}: {e.response.text}")
    except Exception:
        st.error("Unexpected error contacting the API.")
    return None


def _post_file(file_bytes: bytes, filename: str) -> Optional[Any]:
    try:
        r = requests.post(
            f"{API_URL}/documents",
            files={"file": (filename, file_bytes)},
            timeout=60,
        )
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        st.error(f"Cannot connect to API at {API_URL}. Is the server running?")
    except requests.exceptions.HTTPError as e:
        st.error(f"Upload failed ({e.response.status_code}): {e.response.text}")
    except Exception:
        st.error("Unexpected error during upload.")
    return None


def _patch_fields(doc_id: str, fields: dict[str, str]) -> Optional[Any]:
    try:
        r = requests.patch(
            f"{API_URL}/documents/{doc_id}/fields",
            json={"fields": fields},
            timeout=15,
        )
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        st.error(f"Cannot connect to API at {API_URL}.")
    except requests.exceptions.HTTPError as e:
        st.error(f"Save failed ({e.response.status_code}): {e.response.text}")
    except Exception:
        st.error("Unexpected error saving corrections.")
    return None


def _get_file(doc_id: str) -> Optional[bytes]:
    try:
        r = requests.get(f"{API_URL}/documents/{doc_id}/file", timeout=15)
        r.raise_for_status()
        return r.content
    except requests.exceptions.ConnectionError:
        st.error(f"Cannot connect to API at {API_URL}.")
    except requests.exceptions.HTTPError:
        pass  # file simply missing – handled by caller
    except Exception:
        st.error("Unexpected error fetching document file.")
    return None


# ---------------------------------------------------------------------------
# Sidebar – upload widget + filters
# ---------------------------------------------------------------------------

def _sidebar() -> dict:
    """Render sidebar and return current filter state."""
    st.sidebar.title("📄 DocSense")

    # ---- Upload ----
    st.sidebar.header("Upload document")
    uploaded = st.sidebar.file_uploader(
        "Choose a file",
        type=["png", "jpg", "jpeg", "tif", "tiff", "bmp", "pdf"],
    )
    if uploaded and st.sidebar.button("Upload & process"):
        with st.spinner("Uploading & processing…"):
            result = _post_file(uploaded.read(), uploaded.name)
        if result:
            st.sidebar.success(f"✅ Processed: {result['doc_id'][:8]}…")
            st.session_state["selected_doc_id"] = result["doc_id"]
            st.rerun()

    # ---- Search / filter ----
    st.sidebar.header("Search & filter")
    doc_type = st.sidebar.selectbox(
        "Document type",
        ["(all)", "invoice", "receipt", "form", "certificate", "unknown"],
    )
    needs_review = st.sidebar.selectbox(
        "Review status", ["(all)", "Needs review", "OK"]
    )
    vendor = st.sidebar.text_input("Vendor (contains)")
    date_from = st.sidebar.date_input("Date from", value=None)
    date_to = st.sidebar.date_input("Date to", value=None)
    min_amount = st.sidebar.number_input(
        "Min amount", value=0.0, step=1.0, format="%.2f"
    )
    max_amount = st.sidebar.number_input(
        "Max amount", value=0.0, step=1.0, format="%.2f",
        help="Set to 0 to disable"
    )
    limit = st.sidebar.slider("Results per page", 5, 50, 20)
    page = st.sidebar.number_input("Page", min_value=1, value=1, step=1)

    return dict(
        doc_type=None if doc_type == "(all)" else doc_type,
        needs_review=(
            None if needs_review == "(all)"
            else (True if needs_review == "Needs review" else False)
        ),
        vendor=vendor or None,
        date_from=date_from.isoformat() if date_from else None,
        date_to=date_to.isoformat() if date_to else None,
        min_amount=min_amount if min_amount > 0 else None,
        max_amount=max_amount if max_amount > 0 else None,
        limit=limit,
        offset=(page - 1) * limit,
    )


# ---------------------------------------------------------------------------
# Document list panel
# ---------------------------------------------------------------------------

def _document_list(filters: dict) -> None:
    """Render the document list table and allow selecting a document."""
    params = {k: v for k, v in filters.items() if v is not None}
    data = _get("/search", params=params)
    if data is None:
        return

    items = data.get("items", [])
    total = data.get("total", 0)
    st.caption(f"**{total}** documents found")

    if not items:
        st.info("No documents match the current filters.")
        return

    for item in items:
        review_icon = "🔴" if item["needs_review"] else "🟢"
        amount_str = (
            f"  •  \${item['total_amount']:.2f}" if item["total_amount"] else ""
        )
        label = (
            f"{review_icon} **{item['filename']}**  "
            f"`{item['doc_type']}`  "
            f"{item.get('doc_date', '') or ''}  "
            f"{item.get('vendor', '') or ''}{amount_str}"
        )
        if st.button(label, key=f"sel_{item['doc_id']}"):
            st.session_state["selected_doc_id"] = item["doc_id"]
            st.rerun()


# ---------------------------------------------------------------------------
# File preview panel (left column)
# ---------------------------------------------------------------------------

def _preview_file(doc_id: str, doc: dict) -> None:
    """Render the original document file."""
    st.subheader("📎 Document")
    content_type = doc.get("content_type") or ""
    file_bytes = _get_file(doc_id)
    if not file_bytes:
        st.info("No file stored for this document.")
        return

    if content_type.startswith("image/") or doc["filename"].lower().endswith(
        (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp")
    ):
        st.image(file_bytes, use_container_width=True)
    elif content_type == "application/pdf" or doc["filename"].lower().endswith(".pdf"):
        try:
            import fitz  # PyMuPDF

            pdf = fitz.open(stream=file_bytes, filetype="pdf")
            page = pdf[0]
            pix = page.get_pixmap(dpi=150)
            img_bytes = pix.tobytes("png")
            st.image(img_bytes, caption="Page 1 of PDF", use_container_width=True)
        except ImportError:
            st.warning("PyMuPDF not installed – cannot render PDF preview.")
        except Exception:
            st.error("Failed to render PDF page 1.")
    else:
        st.info("File preview not available for this type.")


# ---------------------------------------------------------------------------
# Review & correction panel (right column)
# ---------------------------------------------------------------------------

def _review_panel(doc_id: str, doc: dict) -> None:
    """Render editable fields, validation, tables, and save buttons."""
    st.subheader("🔍 Extracted fields")

    fields = doc.get("fields", {})
    original_values: dict[str, str] = {
        name: (info.get("value") or "") for name, info in fields.items()
    }

    edited: dict[str, str] = {}
    for name, info in fields.items():
        conf = info.get("conf", 0.0)
        val = info.get("value") or ""
        low = conf < LOW_CONF_THRESHOLD

        label_style = "⚠️" if low else "✅"
        label = f"{label_style} **{name}** (conf: {conf:.0%})"
        st.markdown(label)
        new_val = st.text_input(
            f"Edit {name}",
            value=val,
            key=f"field_{doc_id}_{name}",
            label_visibility="collapsed",
        )
        edited[name] = new_val

    # ---- Validation results ----
    st.subheader("🧪 Validation")
    validation = doc.get("validation", [])
    if not validation:
        st.info("No validation rules ran.")
    for result in validation:
        icon = "✅" if result["passed"] else "❌"
        msg = f" — {result['message']}" if result.get("message") else ""
        st.markdown(f"{icon} `{result['rule']}`{msg}")

    # ---- Review status ----
    needs_review = doc.get("needs_review", False)
    if needs_review:
        st.warning("⚠️ This document needs human review.")
    else:
        st.success("✅ Document is verified.")

    # ---- Line items ----
    tables = doc.get("tables", [])
    if tables:
        st.subheader("📋 Line items")
        for i, table in enumerate(tables):
            st.caption(f"Table {i + 1}")
            headers = table.get("headers", [])
            rows = table.get("rows", [])
            if headers and rows:
                import pandas as pd
                df = pd.DataFrame(rows, columns=headers)
                st.dataframe(df, use_container_width=True, hide_index=True)

    # ---- Action buttons ----
    st.divider()
    col_save, col_confirm = st.columns(2)

    with col_save:
        if st.button("💾 Save corrections", type="primary"):
            changed = {
                name: new_val
                for name, new_val in edited.items()
                if new_val != original_values.get(name, "")
            }
            if not changed:
                st.info("No changes to save.")
            else:
                with st.spinner("Saving…"):
                    updated = _patch_fields(doc_id, changed)
                if updated:
                    st.success("Saved! Refreshing…")
                    st.session_state["doc_cache"] = updated
                    st.rerun()

    with col_confirm:
        if st.button("✅ Confirm all (mark as human-verified)"):
            # Send all fields back as-is – this sets conf=1.0 for each
            all_fields = {n: v for n, v in edited.items()}
            if not all_fields:
                st.info("No fields to confirm.")
            else:
                with st.spinner("Confirming…"):
                    updated = _patch_fields(doc_id, all_fields)
                if updated:
                    st.success("All fields confirmed!")
                    st.session_state["doc_cache"] = updated
                    st.rerun()


# ---------------------------------------------------------------------------
# Main layout
# ---------------------------------------------------------------------------

def main():
    filters = _sidebar()

    st.title("Smart Document & Form Intelligence")

    col_list, col_detail = st.columns([1, 2], gap="large")

    with col_list:
        st.header("Documents")
        _document_list(filters)

    selected_id = st.session_state.get("selected_doc_id")

    with col_detail:
        if not selected_id:
            st.info("← Select a document from the list, or upload one using the sidebar.")
            return

        # Use cached version if we just saved, otherwise fetch fresh
        if "doc_cache" in st.session_state:
            doc = st.session_state.pop("doc_cache")
        else:
            doc = _get(f"/documents/{selected_id}")
        if not doc:
            return

        st.header(f"`{selected_id[:12]}…`  —  {doc.get('filename', '')}")
        left, right = st.columns([1, 1], gap="medium")

        with left:
            _preview_file(selected_id, doc)

        with right:
            _review_panel(selected_id, doc)


if __name__ == "__main__":
    main()

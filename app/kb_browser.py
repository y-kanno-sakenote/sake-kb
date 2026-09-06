"""sake-kb を手元のブラウザで引くだけの画面（ローカル専用・公開しない）。

検索と出典表記は scripts/kb.py の search() / cite() をそのまま使う（ADR-018）。
起動: streamlit run app/kb_browser.py --server.port 8530
"""
import os
import sqlite3
import sys

import streamlit as st

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import kb  # noqa: E402  scripts/kb.py
import kbdb  # noqa: E402  scripts/kbdb.py

st.set_page_config(page_title="sake-kb 検索", page_icon="🍶", layout="wide")


@st.cache_data(show_spinner=False)
def load_sources():
    """台帳（sources.csv）と、DB 内のチャンク数。"""
    rows = kbdb.read_sources()
    counts = {}
    if os.path.exists(kb.DB):
        con = sqlite3.connect(kb.DB)
        counts = dict(con.execute("SELECT source_id, COUNT(*) FROM chunks GROUP BY source_id"))
        con.close()
    return rows, counts


def excerpt(r, terms):
    """一致行の抜粋（scripts/kb.py の CLI 出力と同じ切り出し）。"""
    lines = r["text"].split("\n")
    hit_lines = [l for l in lines if any(t in l for t in terms)] if len(lines) > 1 else []
    if hit_lines:
        return " / ".join(hit_lines[:2])[:200] + ("…" if len(hit_lines) > 2 else "")
    return r["text"][:160].replace("\n", " ") + ("…" if len(r["text"]) > 160 else "")


sources, counts = load_sources()

with st.sidebar:
    st.header("出典台帳")
    st.dataframe(
        [
            {
                "source_id": s["source_id"],
                "title": s["title"],
                "tier": s["tier"],
                "type": s["type"],
                "year": s["year"],
                "チャンク": counts.get(s["source_id"], 0),
            }
            for s in sources
        ],
        hide_index=True,
        use_container_width=True,
    )

st.title("🍶 sake-kb 検索")

query = st.text_input("検索語（スペース区切りで AND）", "")
c1, c2 = st.columns([1, 4])
with c1:
    k = st.number_input("件数", min_value=1, max_value=100, value=10, step=1)
with c2:
    labels = {s["source_id"]: f"{s['source_id']} — {s['title']}" for s in sources}
    picked = st.multiselect(
        "出典で絞る（空なら全て）",
        options=list(labels),
        format_func=lambda sid: labels.get(sid, sid),
    )

if query.strip():
    if picked:
        hits = []
        for sid in picked:
            hits += kb.search(query, int(k), sid)
        hits.sort(key=lambda r: r["score"])
        hits = hits[: int(k)]
    else:
        hits = kb.search(query, int(k))

    terms = [t for t in query.split() if t]
    if not hits:
        st.write("0件")
    else:
        st.caption(f"{len(hits)}件")
        for r in hits:
            st.markdown(f"**{kb.cite(r)}**")
            st.write(excerpt(r, terms))
            with st.expander("全文を見る"):
                st.text(r["text"])
            st.divider()

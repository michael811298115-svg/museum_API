# -*- coding: utf-8 -*-
# Explore Artworks — Art Institute of Chicago (AIC) API — Streamlit App
# Not the same as the MET example: uses a different open API, adds filters, and card-style layout.
#
# Run:
#   pip install -r requirements.txt
#   streamlit run aic_explorer_app.py
#
# API docs: https://api.artic.edu/docs/
import math
import requests
import streamlit as st

st.set_page_config(page_title="AIC Artworks Explorer", page_icon="🖼️", layout="wide")
API_SEARCH = "https://api.artic.edu/api/v1/artworks/search"
IIIF_BASE = "https://www.artic.edu/iiif/2"

st.title("🖼️ Art Institute of Chicago — Open API Explorer")
st.caption("Search and filter public-domain artworks via AIC's open API (IIIF images).")

# -----------------------------
# Sidebar controls (different factors vs. the MET app)
# -----------------------------
with st.sidebar:
    st.header("Search & Filters")
    q = st.text_input("Keyword", st.session_state.get("q", "landscape"))
    st.session_state["q"] = q

    st.subheader("Filters")
    has_image = st.checkbox("Only items with images", value=True)
    dept = st.selectbox("Department (optional)", ["Any","Painting and Sculpture","Photography","Textiles","Asian Art","Prints and Drawings","Architecture and Design"])
    date_min, date_max = st.slider("Year range (approx.)", 1200, 2025, (1800, 1950))
    sort = st.selectbox("Sort by", ["relevance","date_asc","date_desc"], index=0)

    st.subheader("Layout")
    per_page = st.slider("Results per page", 3, 30, 9, step=3)
    cols_n = st.radio("Columns", [2,3,4], index=1, horizontal=True)
    show_caption = st.checkbox("Show extra metadata", value=True)

# -----------------------------
# Helpers
# -----------------------------
FIELDS = "id,title,artist_title,date_display,department_title,image_id,is_public_domain"

def _build_params(q, page, limit):
    params = {
        "q": q if q else "",
        "fields": FIELDS,
        "page": page,
        "limit": limit,
    }
    # filter for images
    if has_image:
        params["query[term][is_public_domain]"] = "true"
        params["query[exists][image_id]"] = "true"
    # department filter (best-effort; AIC has many departments)
    if dept != "Any":
        params["query[term][department_title]"] = dept
    # date range (best-effort using range on date_start/date_end)
    params["query[range][date_start][gte]"] = date_min
    params["query[range][date_end][lte]"] = date_max
    # sort
    if sort == "date_asc":
        params["sort"] = "date_start"
        params["order"] = "asc"
    elif sort == "date_desc":
        params["sort"] = "date_start"
        params["order"] = "desc"
    return params

@st.cache_data(show_spinner=False, ttl=600)
def search_aic(q, page=1, limit=9, params_key=""):
    # We pass a derived key so Streamlit cache distinguishes between different filter combos.
    params = _build_params(q, page, limit)
    try:
        r = requests.get(API_SEARCH, params=params, timeout=20)
        r.raise_for_status()
        data = r.json()
        records = data.get("data", [])
        total = (data.get("pagination") or {}).get("total", len(records))
        return {"records": records, "total": total}
    except Exception as e:
        return {"records": [], "total": 0, "error": str(e)}

def iiif_url(image_id, max_w=800):
    # IIIF pattern: https://www.artic.edu/iiif/2/{identifier}/full/{max_w},/0/default.jpg
    return f"{IIIF_BASE}/{image_id}/full/{max_w},/0/default.jpg"

def card(record):
    title = record.get("title") or "Untitled"
    artist = record.get("artist_title") or "Unknown artist"
    date = record.get("date_display") or ""
    dpt = record.get("department_title") or ""
    img_id = record.get("image_id")
    url_work = f"https://www.artic.edu/artworks/{record.get('id')}"
    st.subheader(title)
    if img_id:
        st.image(iiif_url(img_id, 900), use_container_width=True)
    else:
        st.info("No image available")
    st.markdown(f"**Artist**: {artist}")
    if date or dpt:
        st.markdown(f"**Year/Dept**: {date} {('• ' + dpt) if dpt else ''}")
    if show_caption:
        st.caption(f"[Open on AIC]({url_work})  •  Public Domain: {record.get('is_public_domain')}")
    st.markdown("---")

# -----------------------------
# Query + pagination using AIC's native paging
# -----------------------------
page = int(st.query_params.get("page", ["1"])[0] or 1)
page = max(page, 1)
result = search_aic(q, page=page, limit=per_page, params_key=f"{q}-{has_image}-{dept}-{date_min}-{date_max}-{sort}")

total = result.get("total", 0)
st.write(f"**Found:** {total} items")

if total == 0:
    st.info("Try adjusting your filters or keyword (e.g., 'japan', 'portrait', 'seascape').")
else:
    pages = max(1, math.ceil(total / per_page))

    # top navigation
    nav = st.columns(3)
    with nav[0]:
        if st.button("⬅️ Prev", disabled=(page <= 1)):
            st.query_params.update({"page": str(page - 1)})
            st.rerun()
    with nav[1]:
        st.write(f"Page **{page} / {pages}**")
    with nav[2]:
        if st.button("Next ➡️", disabled=(page >= pages)):
            st.query_params.update({"page": str(page + 1)})
            st.rerun()

    # card grid
    columns = st.columns(cols_n)
    i = 0
    for rec in result["records"]:
        with columns[i % cols_n]:
            card(rec)
        i += 1

    # bottom navigation
    nav2 = st.columns(3)
    with nav2[0]:
        if st.button("⬅️ Prev ", key="prev2", disabled=(page <= 1)):
            st.query_params.update({"page": str(page - 1)})
            st.rerun()
    with nav2[1]:
        st.write(f"Page **{page} / {pages}**")
    with nav2[2]:
        if st.button("Next ➡️ ", key="next2", disabled=(page >= pages)):
            st.query_params.update({"page": str(page + 1)})
            st.rerun()

st.divider()
st.caption("Data: Art Institute of Chicago — Public API & IIIF")

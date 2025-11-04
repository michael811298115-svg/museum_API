# streamlit_app.py
# Streamlit app for The Met Museum Open Access API (no API key required)
# Deploy via Streamlit Community Cloud with this file as the entry point.

import requests
import streamlit as st

API_BASE = "https://collectionapi.metmuseum.org/public/collection/v1"

st.set_page_config(page_title="Explore Artworks — MET Open API", page_icon="🖼️", layout="wide")

@st.cache_data(show_spinner=False, ttl=60*60)
def fetch_departments():
    try:
        r = requests.get(f"{API_BASE}/departments", timeout=20)
        r.raise_for_status()
        js = r.json() or {}
        depts = js.get("departments", [])
        # Build mapping: "Name (id)" -> id
        options = ["全部部门"]
        mapping = {"全部部门": None}
        for d in depts:
            label = f"{d.get('displayName','Unknown')} ({d.get('departmentId')})"
            options.append(label)
            mapping[label] = d.get("departmentId")
        return options, mapping
    except Exception:
        # Fallback when API hiccups
        return ["全部部门"], {"全部部门": None}

@st.cache_data(show_spinner=True, ttl=60)
def search_ids(q, has_images=True, department_id=None):
    params = {"q": q, "hasImages": has_images}
    if department_id:
        params["departmentId"] = int(department_id)
    r = requests.get(f"{API_BASE}/search", params=params, timeout=25)
    r.raise_for_status()
    data = r.json() or {}
    return data.get("objectIDs") or [], int(data.get("total", 0))

@st.cache_data(show_spinner=False, ttl=60*60)
def fetch_object(oid: int):
    r = requests.get(f"{API_BASE}/objects/{oid}", timeout=20)
    if r.status_code == 200:
        return r.json()
    return None

# ---- UI ----
st.title("🖼️ Explore Artworks with MET Museum Open API")
st.caption("无需 API Key · 官方开放访问 · 支持关键词与部门过滤")

with st.sidebar:
    st.header("搜索条件")
    q = st.text_input("关键词", value="flower", help="例如：flower, china, landscape, portrait…")
    max_n = st.slider("最多返回（展示）", 1, 60, 18)
    has_images = st.toggle("只看有图", value=True)

    options, mapping = fetch_departments()
    choice = st.selectbox("部门（可选）", options, index=0)
    dept_id = mapping.get(choice)

    search_btn = st.button("开始搜索", type="primary", use_container_width=True)

if search_btn:
    if not q.strip():
        st.warning("请输入关键词后再搜索。")
        st.stop()
    with st.spinner("检索中…"):
        ids, total = search_ids(q.strip(), has_images=has_images, department_id=dept_id)
    st.subheader(f"“{q}” 的结果")
    st.caption(f"总计检索到 {total} 件；当前展示 {min(max_n, len(ids))} 件")
    if not ids:
        st.info("没有检索到结果，试试换个关键词或取消过滤。")
        st.stop()

    cols = st.columns(3)
    for i, oid in enumerate(ids[:max_n]):
        obj = fetch_object(oid)
        if not obj:
            continue
        with cols[i % 3]:
            st.image(obj.get("primaryImageSmall") or obj.get("primaryImage") or "", use_column_width=True)
            st.markdown(f"**{obj.get('title') or 'Untitled'}**")
            artist = obj.get("artistDisplayName") or "Unknown"
            date = obj.get("objectDate") or ""
            st.caption(f"{artist} · {date}")
            if obj.get("medium"):
                st.write(f"材质：{obj.get('medium')}")
            if obj.get("objectURL"):
                st.link_button("在 The Met 查看", obj.get("objectURL"), use_container_width=True)

else:
    st.info("在左侧输入关键词后点击 **开始搜索**，即可浏览藏品。")
    st.divider()
    st.markdown(
        """
        **小贴士**
        - 关键词可以用英文更准（例如 *flower*, *portrait*, *bronze*）
        - “部门”下拉来自官方 `/departments` 接口
        - 该应用仅使用公开 API，无需任何密钥
        """
    )

st.markdown("---")
st.caption("数据来源：The Met Museum Open Access — https://metmuseum.github.io/")

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import os
from pathlib import Path
from anthropic import Anthropic

st.set_page_config(page_title="AI Analytics", page_icon="📊", layout="wide")

LOGS_DIR = os.getenv("LOGS_DIR", "logs/sessions")


@st.cache_data
def load_logs(logs_dir: str) -> pd.DataFrame:
    records = []
    for f in Path(logs_dir).glob("*.json"):
        with open(f) as fp:
            try:
                data = json.load(fp)
                data["file"] = f.name
                records.append(data)
            except json.JSONDecodeError:
                st.warning(f"スキップ: {f.name}（JSONパースエラー）")
    if not records:
        return pd.DataFrame()
    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["date"])
    df["pivot_count"] = pd.to_numeric(df.get("pivot_count", 0), errors="coerce").fillna(0)
    df["resolved"] = df.get("resolution", "").eq("resolved")
    return df


def kpi_cards(df: pd.DataFrame):
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("総セッション数", len(df))
    c2.metric("ユーザー数", df["user"].nunique())
    avg_pivot = df["pivot_count"].mean()
    c3.metric("平均ピボット数", f"{avg_pivot:.1f}")
    resolution_rate = df["resolved"].mean() * 100
    c4.metric("解決率", f"{resolution_rate:.0f}%")


def timeline_chart(df: pd.DataFrame):
    daily = df.groupby("date").size().reset_index(name="count")
    fig = px.bar(daily, x="date", y="count", title="セッション数の推移", labels={"date": "日付", "count": "セッション数"})
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, use_container_width=True)


def pivot_by_user(df: pd.DataFrame):
    fig = px.box(
        df, x="user", y="pivot_count", color="user",
        title="ユーザー別ピボット数分布",
        labels={"user": "ユーザー", "pivot_count": "ピボット数"},
    )
    st.plotly_chart(fig, use_container_width=True)


def category_by_user(df: pd.DataFrame):
    if "category" not in df.columns:
        st.info("categoryフィールドがありません")
        return
    cross = df.groupby(["user", "category"]).size().reset_index(name="count")
    fig = px.bar(
        cross, x="user", y="count", color="category", barmode="stack",
        title="ユーザー別カテゴリ分布",
        labels={"user": "ユーザー", "count": "セッション数", "category": "カテゴリ"},
    )
    st.plotly_chart(fig, use_container_width=True)


def resolution_by_user(df: pd.DataFrame):
    rate = (
        df.groupby("user")["resolved"]
        .agg(resolved="sum", total="count")
        .assign(rate=lambda x: x["resolved"] / x["total"] * 100)
        .reset_index()
    )
    fig = px.bar(
        rate, x="user", y="rate", color="user",
        title="ユーザー別解決率 (%)",
        labels={"user": "ユーザー", "rate": "解決率 (%)"},
        range_y=[0, 100],
    )
    st.plotly_chart(fig, use_container_width=True)


def text_analysis(df: pd.DataFrame, selected_user: str | None):
    st.subheader("AIによるパターン分析")
    target = df if not selected_user else df[df["user"] == selected_user]

    if target.empty:
        st.info("データがありません")
        return

    entries = []
    for _, row in target.iterrows():
        entries.append(
            f"【{row.get('user', '?')} / {row.get('date', '?').date()} / {row.get('category', '?')}】\n"
            f"問題: {row.get('problem', '')}\n"
            f"アプローチ: {row.get('approach', '')}\n"
            f"主要決定: {'; '.join(row.get('key_decisions', []))}\n"
            f"ピボット数: {row.get('pivot_count', 0)}"
        )

    prompt = f"""以下はチームメンバーのAI壁打ちセッションログです。
各メンバーのプロンプトの癖・思考パターン・よく使うアプローチを分析し、
開発効率化に役立つ洞察を日本語で提供してください。

{chr(10).join(entries)}

以下の観点で分析してください：
1. ユーザーごとの思考・アプローチの特徴
2. ピボット（方向転換）が多い場合のパターン
3. チーム全体として改善できそうな点"""

    api_key = st.secrets.get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        st.warning("ANTHROPIC_API_KEY が設定されていません。`.streamlit/secrets.toml` に追加してください。")
        with st.expander("プロンプト（手動でClaudeに貼り付ける用）"):
            st.code(prompt)
        return

    client = Anthropic(api_key=api_key)
    with st.spinner("Claudeが分析中..."):
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
    st.markdown(response.content[0].text)


# ── Main ──────────────────────────────────────────────────────────────────────

st.title("📊 AI壁打ち Analytics")

df = load_logs(LOGS_DIR)

if df.empty:
    st.error(f"ログが見つかりません: `{LOGS_DIR}`")
    st.stop()

# Sidebar filters
st.sidebar.header("フィルター")
users = ["全員"] + sorted(df["user"].unique().tolist())
selected_user = st.sidebar.selectbox("ユーザー", users)
filtered = df if selected_user == "全員" else df[df["user"] == selected_user]

date_range = st.sidebar.date_input(
    "期間",
    value=(df["date"].min().date(), df["date"].max().date()),
)
if len(date_range) == 2:
    start, end = date_range
    filtered = filtered[(filtered["date"].dt.date >= start) & (filtered["date"].dt.date <= end)]

st.sidebar.markdown(f"**{len(filtered)}** 件のセッション")

if st.sidebar.button("キャッシュ更新"):
    st.cache_data.clear()
    st.rerun()

# Tabs
tab1, tab2, tab3 = st.tabs(["📈 概要", "👤 ユーザー別", "🤖 テキスト分析"])

with tab1:
    kpi_cards(filtered)
    st.divider()
    timeline_chart(filtered)

with tab2:
    pivot_by_user(filtered)
    col1, col2 = st.columns(2)
    with col1:
        category_by_user(filtered)
    with col2:
        resolution_by_user(filtered)

    st.subheader("セッション一覧")
    cols = [c for c in ["date", "user", "category", "topic", "pivot_count", "resolution"] if c in filtered.columns]
    st.dataframe(filtered[cols].sort_values("date", ascending=False), use_container_width=True)

with tab3:
    user_for_analysis = None if selected_user == "全員" else selected_user
    if st.button("分析を実行"):
        text_analysis(filtered, user_for_analysis)

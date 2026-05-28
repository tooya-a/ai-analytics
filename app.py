import re
import subprocess
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import os
from datetime import datetime
from pathlib import Path
from anthropic import Anthropic

st.set_page_config(page_title="AI Analytics", page_icon="📊", layout="wide")

st.markdown("""
<style>
div[data-testid="stToast"] {
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    z-index: 9999;
}
</style>
""", unsafe_allow_html=True)

LOGS_DIR = os.getenv("LOGS_DIR", "logs/sessions")

try:
    _DEFAULT_USER = subprocess.check_output(["git", "config", "user.name"], text=True).strip()
except Exception:
    _DEFAULT_USER = ""

_home = Path.home()
_encoded = str(Path.cwd()).replace("/", "-")
TRANSCRIPT_DIR = _home / ".claude" / "projects" / _encoded


@st.cache_data(ttl=30)
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
    df["date"] = pd.to_datetime(df["date"]).fillna(pd.Timestamp.now().normalize())
    df["pivot_count"] = pd.to_numeric(df.get("pivot_count", 0), errors="coerce").fillna(0)
    df["resolved"] = df.get("resolution", "").eq("resolved")
    # blockers は list で来る想定。欠損や非リストは空 list に正規化。
    if "blockers" in df.columns:
        df["blockers"] = df["blockers"].apply(lambda x: x if isinstance(x, list) else [])
    else:
        df["blockers"] = [[] for _ in range(len(df))]
    df["has_blockers"] = df["blockers"].apply(lambda x: len(x) > 0)
    df["unresolved_blocker"] = (~df["resolved"]) & df["has_blockers"]
    return df


def save_log(data: dict, logs_dir: str) -> str:
    topic_slug = re.sub(r"[^\w]", "_", data["topic"].lower())[:40]
    user = data.get("user") or _DEFAULT_USER or "unknown"
    filename = f"{data['date']}-{user}-{topic_slug}.json"
    path = Path(logs_dir) / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return str(path)


def kpi_cards(df: pd.DataFrame):
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("総セッション数", len(df))
    c2.metric("ユーザー数", df["user"].nunique() if "user" in df.columns else 0)
    avg_pivot = df["pivot_count"].mean() if not df.empty else 0.0
    c3.metric("平均ピボット数", f"{avg_pivot:.1f}" if not pd.isna(avg_pivot) else "0.0")
    resolution_rate = df["resolved"].mean() * 100 if not df.empty else 0.0
    c4.metric("解決率", f"{resolution_rate:.0f}%" if not pd.isna(resolution_rate) else "0%")
    unresolved_blocker_count = int(df["unresolved_blocker"].sum()) if "unresolved_blocker" in df.columns else 0
    c5.metric("未解決ブロッカー", f"{unresolved_blocker_count}件", help="resolution が resolved 以外 かつ blockers が記録されているセッション数")


def unresolved_blockers_list(df: pd.DataFrame):
    """未解決のまま終わったセッションの blockers を一覧表示する。"""
    if df.empty or "unresolved_blocker" not in df.columns:
        return
    target = df[df["unresolved_blocker"]].sort_values("date", ascending=False)
    if target.empty:
        return
    with st.expander(f"🚧 未解決ブロッカーの中身を見る（{len(target)}件）"):
        st.caption("解決せずに終わったセッションです。気づいた人が声をかけたり、知見を共有しましょう。")
        for _, row in target.iterrows():
            user = row.get("user", "?")
            date = row["date"].date() if pd.notna(row.get("date")) else "?"
            topic = row.get("topic", "")
            blockers = row.get("blockers", []) or []
            header = f"**{user}** ／ {date}"
            if topic:
                header += f" ／ {topic}"
            st.markdown(header)
            for b in blockers:
                st.markdown(f"- {b}")


def timeline_chart(df: pd.DataFrame):
    if df.empty:
        st.caption("データがありません")
        return
    daily = df.groupby("date").size().reset_index(name="count")
    fig = px.bar(daily, x="date", y="count", title="セッション数の推移", labels={"date": "日付", "count": "セッション数"})
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, use_container_width=True)


def pivot_by_user(df: pd.DataFrame):
    if df.empty:
        st.caption("データがありません")
        return
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
    if df.empty:
        st.caption("データがありません")
        return
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


def blockers_by_user(df: pd.DataFrame):
    """ユーザー別のブロッカー一覧。頻出ワードではなく原文をそのまま並べる（件数が少ない前提）。"""
    if df.empty or "blockers" not in df.columns:
        return
    exploded = df[["user", "blockers"]].explode("blockers").dropna(subset=["blockers"])
    exploded = exploded[exploded["blockers"].astype(str).str.len() > 0]
    if exploded.empty:
        st.caption("ブロッカーの記録がありません")
        return
    st.subheader("ユーザー別ブロッカー")
    counts = exploded.groupby("user").size().reset_index(name="count")
    fig = px.bar(
        counts, x="user", y="count", color="user",
        title="ユーザー別ブロッカー件数",
        labels={"user": "ユーザー", "count": "ブロッカー件数"},
    )
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, use_container_width=True)
    with st.expander("ブロッカー内容を見る"):
        for user, group in exploded.groupby("user"):
            st.markdown(f"**{user}**")
            for b in group["blockers"]:
                st.markdown(f"- {b}")


def text_analysis(df: pd.DataFrame, selected_user: str | None):
    st.subheader("AIによるパターン分析")
    target = df if not selected_user else df[df["user"] == selected_user]

    if target.empty:
        st.info("データがありません")
        return

    entries = []
    for _, row in target.iterrows():
        blockers = row.get("blockers", []) or []
        entries.append(
            f"【{row.get('user', '?')} / {row.get('date', '?').date()} / {row.get('category', '?')}】\n"
            f"問題: {row.get('problem', '')}\n"
            f"アプローチ: {row.get('approach', '')}\n"
            f"主要決定: {'; '.join(row.get('key_decisions', []))}\n"
            f"ブロッカー: {'; '.join(blockers) if blockers else 'なし'}\n"
            f"解決状態: {row.get('resolution', '?')}\n"
            f"ピボット数: {row.get('pivot_count', 0)}"
        )

    prompt = f"""以下はチームメンバーのAI壁打ちセッションログです。
各メンバーのプロンプトの癖・思考パターン・よく使うアプローチを分析し、
開発効率化に役立つ洞察を日本語で提供してください。

{chr(10).join(entries)}

以下の観点で分析してください：
1. ユーザーごとの思考・アプローチの特徴
2. ピボット（方向転換）が多い場合のパターン
3. チーム全体として改善できそうな点
4. 頻出するブロッカー（詰まりポイント）と、共通する原因・ナレッジ共有の余地"""

    try:
        try:
            api_key = st.secrets.get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        except Exception:
            api_key = os.getenv("ANTHROPIC_API_KEY")
    except Exception:
        api_key = os.getenv("ANTHROPIC_API_KEY")
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


def load_latest_transcript(transcript_dir: Path) -> list[dict]:
    files = sorted(transcript_dir.glob("*.jsonl"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not files:
        return []
    messages = []
    for line in files[0].open(encoding="utf-8"):
        try:
            obj = json.loads(line)
            if obj.get("type") not in ("user", "assistant"):
                continue
            role = obj["type"]
            content = obj.get("message", {}).get("content", "")
            if isinstance(content, list):
                content = " ".join(c.get("text", "") for c in content if isinstance(c, dict))
            if content.strip():
                messages.append({"role": role, "content": content[:2000]})
        except Exception:
            continue
    return messages


def generate_log_from_transcript(messages: list[dict], api_key: str) -> dict:
    client = Anthropic(api_key=api_key)
    prompt = f"""以下はClaude Codeのセッション会話です。内容を分析し、下記のJSON形式でセッションログを生成してください。
値が不明な場合はnullまたは空配列にしてください。JSONのみ出力してください。

スキーマ:
{{
  "user": "{_DEFAULT_USER}",
  "date": "YYYY-MM-DD",
  "started_at": "HH:MM",
  "category": "bug_fix|feature|design|refactor|infrastructure|question",
  "topic": "1行の説明",
  "problem": "解こうとした課題",
  "approach": "試行錯誤の流れ",
  "resolution": "resolved|unresolved|in_progress",
  "output": "成果物またはnull",
  "pivot_count": 0,
  "key_decisions": ["決定1"],
  "blockers": [],
  "notes": null
}}

会話:
{json.dumps(messages, ensure_ascii=False)[:8000]}
"""
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.content[0].text.strip()
    text = re.sub(r"^```[a-z]*\n?", "", text)
    text = re.sub(r"\n?```$", "", text)
    return json.loads(text)


CATEGORIES = ["bug_fix", "feature", "design", "refactor", "infrastructure", "question"]
RESOLUTIONS = ["resolved", "unresolved", "in_progress"]


def manual_log_form(logs_dir: str):
    st.subheader("セッションログを手入力で記録")
    st.caption("`/session-log` スキルを使わずに、ブラウザから直接ログを記録できます。")

    with st.form("manual_log_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        user = c1.text_input("ユーザー名", value=_DEFAULT_USER or "")
        date = c2.date_input("日付", value=datetime.now().date())
        started_at = c3.text_input("開始時刻 (HH:MM)", value=datetime.now().strftime("%H:%M"))

        c4, c5 = st.columns(2)
        category = c4.selectbox("カテゴリ", CATEGORIES)
        resolution = c5.selectbox("解決状況", RESOLUTIONS)

        topic = st.text_input("トピック（1行で）", placeholder="例: ログ記録フォームの追加")
        problem = st.text_area("解こうとした課題", height=80)
        approach = st.text_area("試行錯誤の流れ", height=120)
        output = st.text_input("成果物（任意）", placeholder="例: app.py の manual_log_form 関数")

        c6, c7 = st.columns(2)
        pivot_count = c6.number_input("ピボット回数", min_value=0, value=0, step=1)
        key_decisions_text = c7.text_area("主要な意思決定（1行1項目）", height=80)

        blockers_text = st.text_area("ブロッカー（1行1項目）", height=60)
        notes = st.text_area("メモ（任意）", height=60)

        submitted = st.form_submit_button("💾 保存する", use_container_width=True)

    if submitted:
        if not topic.strip():
            st.error("トピックは必須です。")
            return
        if not user.strip():
            st.error("ユーザー名は必須です。")
            return

        data = {
            "user": user.strip(),
            "date": date.isoformat(),
            "started_at": started_at.strip() or None,
            "category": category,
            "topic": topic.strip(),
            "problem": problem.strip(),
            "approach": approach.strip(),
            "resolution": resolution,
            "output": output.strip() or None,
            "pivot_count": int(pivot_count),
            "key_decisions": [line.strip() for line in key_decisions_text.splitlines() if line.strip()],
            "blockers": [line.strip() for line in blockers_text.splitlines() if line.strip()],
            "notes": notes.strip() or None,
        }
        path = save_log(data, logs_dir)
        st.cache_data.clear()
        st.success(f"保存しました: `{path}`")
        st.toast("ログを保存しました。サイドバーの「キャッシュ更新」または再読み込みで一覧に反映されます。", icon="✅")


def log_form(logs_dir: str):
    st.subheader("セッションログを自動生成")

    try:
        try:
            api_key = st.secrets.get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        except Exception:
            api_key = os.getenv("ANTHROPIC_API_KEY")
    except Exception:
        api_key = os.getenv("ANTHROPIC_API_KEY")

    col, _ = st.columns([2, 3])
    if col.button("🔍 直近のセッションを分析してログを生成", use_container_width=True):
        if not api_key:
            st.toast("ANTHROPIC_API_KEY が未設定です。`.streamlit/secrets.toml` に追加してください。", icon="🔑")
            return
        messages = load_latest_transcript(TRANSCRIPT_DIR)
        if not messages:
            st.toast(f"トランスクリプトが見つかりません: {TRANSCRIPT_DIR}", icon="⚠️")
            return
        with st.spinner("Claudeが会話を分析中..."):
            try:
                data = generate_log_from_transcript(messages, api_key)
                st.session_state["generated_log"] = data
            except Exception as e:
                st.error(f"生成に失敗しました: {e}")
                return

    if "generated_log" in st.session_state:
        data = st.session_state["generated_log"]
        st.subheader("生成されたログ")
        st.json(data)
        col, _ = st.columns([2, 3])
        if col.button("💾 保存する", use_container_width=True):
            path = save_log(data, logs_dir)
            st.cache_data.clear()
            st.success(f"保存しました: `{path}`")
            del st.session_state["generated_log"]


# ── Main ──────────────────────────────────────────────────────────────────────

st.title("📊 AI壁打ち Analytics")

df = load_logs(LOGS_DIR)

if df.empty:
    st.info(f"ログがまだありません（`{LOGS_DIR}`）。/session-log スキルで記録を始めましょう。")

# Sidebar filters
st.sidebar.header("フィルター")
users = ["全員"] + (sorted(df["user"].unique().tolist()) if not df.empty and "user" in df.columns else [])
selected_user = st.sidebar.selectbox("ユーザー", users)
filtered = df if selected_user == "全員" else df[df["user"] == selected_user]

_today = pd.Timestamp.now().date()
_valid_dates = df["date"].dropna() if not df.empty and "date" in df.columns else pd.Series([], dtype="datetime64[ns]")
_date_default = (_valid_dates.min().date(), _valid_dates.max().date()) if not _valid_dates.empty else (_today, _today)
date_range = st.sidebar.date_input(
    "期間",
    value=_date_default,
)
if len(date_range) == 2 and not filtered.empty and "date" in filtered.columns:
    start, end = date_range
    filtered = filtered[(filtered["date"] >= pd.Timestamp(start)) & (filtered["date"] <= pd.Timestamp(end))]

st.sidebar.markdown(f"**{len(filtered)}** 件のセッション")

if st.sidebar.button("キャッシュ更新"):
    st.cache_data.clear()
    st.rerun()

# Tabs
tab1, tab2, tab_log, tab3 = st.tabs(["📈 概要", "👤 ユーザー別", "📝 ログ記録", "🤖 AI機能"])

with tab1:
    kpi_cards(filtered)
    unresolved_blockers_list(filtered)
    st.divider()
    timeline_chart(filtered)

with tab2:
    pivot_by_user(filtered)
    col1, col2 = st.columns(2)
    with col1:
        category_by_user(filtered)
    with col2:
        resolution_by_user(filtered)

    blockers_by_user(filtered)

    st.subheader("セッション一覧")
    cols = [c for c in ["date", "user", "category", "topic", "pivot_count", "resolution"] if c in filtered.columns]
    display_df = filtered[cols].sort_values("date", ascending=False) if "date" in filtered.columns else filtered[cols]
    st.dataframe(display_df, use_container_width=True)

with tab_log:
    manual_log_form(LOGS_DIR)

with tab3:
    log_form(LOGS_DIR)
    st.divider()
    user_for_analysis = None if selected_user == "全員" else selected_user
    if st.button("パターン分析を実行"):
        text_analysis(filtered, user_for_analysis)

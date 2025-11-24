import streamlit as st
from openai import OpenAI
from typing import List, Dict, Any
import json
import base64
import io
import re


st.set_page_config(page_title="케이크 디자이너 챗봇 🎂", page_icon="🍰", layout="wide")


def get_api_key() -> str:
    # 1) Try Streamlit secrets
    try:
        val = st.secrets.get("OPENAI_API_KEY")
        if val:
            return val
    except Exception:
        # ignore - streamlit might not expose secrets in some environments
        pass

    # 2) Try environment variable
    import os

    env = os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENAIAPIKEY")
    if env:
        return env

    # 3) Try reading .streamlit/secrets.toml directly as last resort (do not log key)
    try:
        base = os.path.join(os.getcwd(), ".streamlit", "secrets.toml")
        if os.path.exists(base):
            with open(base, "r", encoding="utf-8") as f:
                for line in f:
                    if "OPENAI_API_KEY" in line:
                        # naive parse: find first quoted substring
                        m = re.search(r'OPENAI_API_KEY\s*=\s*"([^"]+)"', line)
                        if m:
                            return m.group(1)
    except Exception:
        pass

    return ""


def init_session_state():
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "last_assistant" not in st.session_state:
        st.session_state.last_assistant = ""


def build_system_prompt() -> str:
    return (
        "당신은 숙련된 케이크 디자이너 어시스턴트입니다. 사용자는 케이크 디자이너이며, "
        "소비자의 요구나 최신 트렌드를 반영한 케이크 디자인 메뉴를 개발하려고 합니다. "
        "추천은 색상, 질감, 맛, 식감, 빵 종류, 데코레이션 아이디어, 서빙/계절 제안 등을 포함해야 합니다. "
        "응답은 친절하고 실용적이며, 구체적인 대안(예: 3가지 제안)을 포함하세요."
    )


def create_openai_client(api_key: str) -> OpenAI:
    return OpenAI(api_key=api_key)


def call_chat_api(client: OpenAI, messages: List[Dict[str, Any]], model: str = "gpt-4o-mini") -> str:
    try:
        resp = client.chat.completions.create(model=model, messages=messages, temperature=0.7)
        content = None
        if getattr(resp, "choices", None):
            ch = resp.choices[0]
            # New SDK may have message as dict-like
            content = getattr(ch, "message", None)
            if isinstance(content, dict):
                content = content.get("content")
            elif content and hasattr(content, "get"):
                content = content.get("content")
        if not content:
            return str(resp)
        return content
    except Exception as e:
        return f"오류: {e}"


@st.cache_data(show_spinner=False)
def generate_image_cached(api_key: str, prompt: str, size: str = "512x512") -> bytes:
    client = create_openai_client(api_key)
    try:
        resp = client.images.generate(model="gpt-image-1", prompt=prompt, size=size)
        b64 = resp.data[0].b64_json
        img_bytes = base64.b64decode(b64)
        return img_bytes
    except Exception as e:
        raise RuntimeError(f"이미지 생성 중 오류: {e}")


def parse_suggestions(text: str) -> List[Dict[str, Any]]:
    # Try parse JSON first
    try:
        obj = json.loads(text)
        # Expect structure {"suggestions": [ ... ]}
        if isinstance(obj, dict):
            if "suggestions" in obj and isinstance(obj["suggestions"], list):
                return obj["suggestions"]
            # if direct list
            if isinstance(obj.get("items"), list):
                return obj.get("items")
        if isinstance(obj, list):
            return obj
    except Exception:
        pass

    # Fallback: split by numbered headings (제안 1 / 1.)
    parts = re.split(r"(?:제안|추천)\s*\d+[:\.)]?|^\d+[:\.)]", text)
    suggestions = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        # first line as title
        lines = p.splitlines()
        title = lines[0].strip()
        body = "\n".join(lines[1:]).strip() if len(lines) > 1 else p
        suggestions.append({"title": title or p[:30], "description": body or p})
    if not suggestions:
        suggestions = [{"title": "제안", "description": text}]
    return suggestions


def create_baker_summary(client: OpenAI, assistant_text: str) -> str:
    sys = "당신은 친근한 제빵사 캐릭터입니다. 아래 추천 내용을 짧고 매력적으로 요약해 주세요 (2-3문장). 이모지와 말투를 사용하세요."
    messages = [
        {"role": "system", "content": sys},
        {"role": "user", "content": assistant_text},
    ]
    return call_chat_api(client, messages, model="gpt-4o-mini")


def render_card(idx: int, suggestion: Dict[str, Any], api_key: str):
    title = suggestion.get("title") or suggestion.get("name") or f"제안 {idx+1}"
    desc = suggestion.get("description") or suggestion.get("details") or ""
    colors = suggestion.get("colors") or suggestion.get("color")
    texture = suggestion.get("texture")
    flavor = suggestion.get("flavor") or suggestion.get("taste")
    cake_base = suggestion.get("cake_base") or suggestion.get("빵 종류")
    tips = suggestion.get("tips") or suggestion.get("tips_and_tricks")

    container = st.container()
    with container:
        left, right = st.columns([1, 3])
        with left:
            placeholder = st.empty()
            btn = st.button("이미지 생성", key=f"img_btn_{idx}")
            if btn:
                # build image prompt
                p_parts = [title]
                if colors:
                    p_parts.append(f"colors: {colors}")
                if texture:
                    p_parts.append(f"texture: {texture}")
                if flavor:
                    p_parts.append(f"flavor: {flavor}")
                prompt = ", ".join(p_parts) + ", high quality photo of a cake, studio lighting"
                try:
                    img_bytes = generate_image_cached(api_key, prompt, size="512x512")
                    placeholder.image(img_bytes, use_column_width=True)
                except Exception as e:
                    placeholder.error(str(e))
        with right:
            st.markdown(f"#### 🍰 {title}")
            if colors:
                st.markdown(f"**색상 제안:** {colors}")
            if texture:
                st.markdown(f"**질감:** {texture}")
            if flavor:
                st.markdown(f"**맛/재료:** {flavor}")
            if cake_base:
                st.markdown(f"**빵 종류:** {cake_base}")
            if tips:
                st.markdown(f"**제작 팁:** {tips}")
            st.markdown(desc)
        st.markdown("---")


def render_chat():
    st.title("케이크 디자이너 챗봇 🍰")
    st.write("디자이너로서 고객 요구에 맞춰 색상, 질감, 맛, 식감, 빵 종류 등을 추천받으세요.")

    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("초기화"):  # clear chat
            st.session_state.messages = []
            st.session_state.last_assistant = ""

    # show chat history (compact)
    for msg in st.session_state.messages[-6:]:
        if msg["role"] == "user":
            st.markdown(f"**나:** {msg['content']}")
        elif msg["role"] == "assistant":
            txt = msg["content"].strip()
            if not txt.startswith("🍰"):
                txt = "🍰 " + txt
            st.markdown(f"**챗봇:** {txt}")

    # user input
    with st.form(key="input_form", clear_on_submit=True):
        user_input = st.text_input("질문 또는 요청을 입력하세요 (예: 봄 결혼식용 트렌디한 3가지 케이크 추천):")
        submitted = st.form_submit_button("전송")

    if submitted and user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})

        system_prompt = build_system_prompt()
        api_messages = [{"role": "system", "content": system_prompt}]
        for m in st.session_state.messages[-12:]:
            api_messages.append({"role": m["role"], "content": m["content"]})

        api_key = get_api_key()
        if not api_key:
            st.error("서버에 설정된 OpenAI API 키가 없습니다. `.streamlit/secrets.toml`에 `OPENAI_API_KEY`를 설정해 주세요.")
            return

        client = create_openai_client(api_key)
        with st.spinner("챗봇이 답변을 생성 중입니다..."):
            assistant_reply = call_chat_api(client, api_messages, model="gpt-4o-mini")

        st.session_state.messages.append({"role": "assistant", "content": assistant_reply})
        st.session_state.last_assistant = assistant_reply
        st.experimental_rerun()

    # If there's a last assistant reply, render suggestions as cards
    if st.session_state.last_assistant:
        assistant_text = st.session_state.last_assistant
        suggestions = parse_suggestions(assistant_text)
        st.markdown("## 추천 결과")
        for i, s in enumerate(suggestions):
            render_card(i, s, get_api_key())

        # baker summary
        if st.button("제빵사 요약 보기 🧁"):
            api_key = get_api_key()
            client = create_openai_client(api_key)
            with st.spinner("제빵사 요약 생성 중..."):
                summary = create_baker_summary(client, assistant_text)
            st.info(summary)


def main():
    init_session_state()
    if not get_api_key():
        st.error("`.streamlit/secrets.toml`에 `OPENAI_API_KEY`가 설정되어 있지 않습니다. 앱이 작동하려면 키가 필요합니다.")
    render_chat()


if __name__ == "__main__":
    main()


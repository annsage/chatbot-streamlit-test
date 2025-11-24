import streamlit as st
from openai import OpenAI
from typing import List, Dict, Any
import json
import base64
import re
import os


st.set_page_config(
    page_title="디자인 트렌드 추천봇 🎨",
    page_icon="🍰",
    layout="wide"
)


def get_api_key() -> str:
    """Get API key from secrets, env vars, or direct file read."""
    # 1) Try Streamlit secrets
    try:
        val = st.secrets.get("OPENAI_API_KEY")
        if val:
            return val
    except Exception:
        pass

    # 2) Try environment variable
    env = os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENAIAPIKEY")
    if env:
        return env

    # 3) Try reading .streamlit/secrets.toml directly as last resort
    try:
        base = os.path.join(os.getcwd(), ".streamlit", "secrets.toml")
        if os.path.exists(base):
            with open(base, "r", encoding="utf-8") as f:
                for line in f:
                    if "OPENAI_API_KEY" in line:
                        m = re.search(r'OPENAI_API_KEY\s*=\s*"([^"]+)"', line)
                        if m:
                            return m.group(1)
    except Exception:
        pass

    return ""


def init_session_state():
    """Initialize session state variables."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "last_assistant" not in st.session_state:
        st.session_state.last_assistant = ""
    if "event_type" not in st.session_state:
        st.session_state.event_type = None
    if "design_styles" not in st.session_state:
        st.session_state.design_styles = []
    if "generated_images" not in st.session_state:
        st.session_state.generated_images = {}


EVENTS = [
    "🎄 크리스마스",
    "💍 결혼식",
    "🎉 개업/파티",
    "🎂 생일",
    "💝 발렌타인데이",
    "👰 신혼",
    "🎓 졸업",
    "🏠 집들이",
    "🌸 봄 축제",
    "🌙 추석/명절",
]

DESIGN_CATEGORIES = {
    "케이크": "cake design",
    "벽지": "wallpaper design",
    "일러스트": "illustration design",
    "웹사이트": "website design",
    "배경화면": "background wallpaper",
    "포스터": "poster design",
    "로고": "logo design",
    "패키징": "packaging design",
}

COUNTRIES = ["한국", "일본", "미국", "유럽", "북유럽", "프랑스"]


def build_system_prompt(event_type: str, design_styles: List[str], countries: List[str]) -> str:
    """Build comprehensive prompt for diverse design recommendations."""
    styles_text = ", ".join(design_styles) if design_styles else "케이크"
    countries_text = ", ".join(countries) if countries else "한국"
    
    return (
        f"당신은 창의적인 디자인 큐레이터입니다. 사용자가 '{event_type}' 이벤트에 대해 "
        f"다음 디자인 카테고리의 추천을 요청했습니다: {styles_text}. "
        f"다음 국가/지역의 트렌드도 반영해 주세요: {countries_text}. "
        f"\n\n응답 방식:\n"
        f"1. 각 디자인 카테고리마다 2-3가지 구체적인 아이디어를 제시하세요.\n"
        f"2. 색상 팔레트, 스타일 특징, 영감 출처를 포함하세요.\n"
        f"3. 각 제안은 명확한 제목과 상세 설명으로 구성하세요.\n"
        f"4. 최신 트렌드와 국가별 특징을 반영하세요.\n"
        f"5. 실제로 적용 가능한 구체적인 팁을 제공하세요."
    )


def create_openai_client(api_key: str) -> OpenAI:
    """Create OpenAI client."""
    return OpenAI(api_key=api_key)


def call_chat_api(
    client: OpenAI,
    messages: List[Dict[str, Any]],
    model: str = "gpt-4o-mini"
) -> str:
    """Call OpenAI Chat API."""
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.8
        )
        content = None
        if getattr(resp, "choices", None):
            ch = resp.choices[0]
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
def search_image_free(
    api_key: str,
    prompt: str,
    size: str = "512x512"
) -> str:
    """Search for free image from Unsplash using keyword."""
    try:
        import urllib.request
        import json as json_lib
        
        # Use Unsplash API to search for images
        # Extract key search term from prompt
        search_term = prompt.split(",")[0].strip()[:50]
        
        # Unsplash API endpoint (free tier, no key needed for basic usage)
        url = f"https://api.unsplash.com/search/photos?query={search_term}&per_page=1&order_by=relevant"
        
        # Add User-Agent header (required by Unsplash)
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "CakeDesignBot/1.0"}
        )
        
        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json_lib.loads(response.read().decode())
                if data.get("results") and len(data["results"]) > 0:
                    return data["results"][0]["urls"]["regular"]
        except Exception:
            # Fallback: return a generic image URL if API fails
            pass
        
        # Fallback URLs for different design types
        fallback_urls = {
            "케이크": "https://images.unsplash.com/photo-1578985545062-69928b1d9587?w=500&h=500&fit=crop",
            "벽지": "https://images.unsplash.com/photo-1561070791-2526d30994b5?w=500&h=500&fit=crop",
            "일러스트": "https://images.unsplash.com/photo-1579783902614-e3fb446b9c1f?w=500&h=500&fit=crop",
            "웹사이트": "https://images.unsplash.com/photo-1561070791-2526d30994b5?w=500&h=500&fit=crop",
            "배경화면": "https://images.unsplash.com/photo-1557821552-17105176677c?w=500&h=500&fit=crop",
            "포스터": "https://images.unsplash.com/photo-1547887537-6158d64a96a1?w=500&h=500&fit=crop",
            "로고": "https://images.unsplash.com/photo-1561070791-2526d30994b5?w=500&h=500&fit=crop",
            "패키징": "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=500&h=500&fit=crop",
        }
        
        # Return fallback or search term matched URL
        return fallback_urls.get("케이크", "https://images.unsplash.com/photo-1578985545062-69928b1d9587?w=500&h=500&fit=crop")
    except Exception as e:
        raise RuntimeError(f"이미지 검색 중 오류: {str(e)[:50]}")


def parse_suggestions(text: str) -> List[Dict[str, Any]]:
    """Parse AI response into structured suggestions."""
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            if "suggestions" in obj and isinstance(obj["suggestions"], list):
                return obj["suggestions"]
            if isinstance(obj.get("items"), list):
                return obj.get("items")
        if isinstance(obj, list):
            return obj
    except Exception:
        pass

    # Fallback: split by numbered headings
    parts = re.split(
        r"(?:제안|추천|아이디어)\s*\d+[:\.)]?|^\d+[:\.)]",
        text
    )
    suggestions = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        lines = p.splitlines()
        title = lines[0].strip()
        body = "\n".join(lines[1:]).strip() if len(lines) > 1 else p
        suggestions.append({
            "title": title or p[:40],
            "description": body or p
        })
    
    if not suggestions:
        suggestions = [{"title": "추천", "description": text}]
    return suggestions


def render_design_card(
    idx: int,
    suggestion: Dict[str, Any],
    api_key: str,
    event_type: str,
    design_styles: List[str]
) -> None:
    """Render a design recommendation card with auto-generated image and dual-column layout."""
    title = suggestion.get("title") or f"제안 {idx+1}"
    desc = suggestion.get("description") or ""
    
    with st.container():
        col_left, col_right = st.columns([1, 1.2])
        
        # Left: Image
        with col_left:
            img_placeholder = st.empty()
            
            # Auto-search for image on card render (without button)
            cache_key = f"{event_type}_{title}_{idx}"
            
            if cache_key not in st.session_state.generated_images:
                with st.spinner(f"무료 이미지 검색 중... ({title})"):
                    try:
                        # Build image search keyword
                        styles_str = ", ".join(design_styles) if design_styles else "여러 디자인 스타일"
                        search_query = (
                            f"{event_type} {styles_str}"
                        )
                        img_url = search_image_free(
                            api_key,
                            search_query,
                        )
                        st.session_state.generated_images[cache_key] = img_url
                    except Exception as e:
                        img_placeholder.warning(f"이미지 검색 실패 (무료 이미지 사용)")
                        st.session_state.generated_images[cache_key] = None
            
            # Display cached image (as link + embedded)
            if cache_key in st.session_state.generated_images:
                img_url = st.session_state.generated_images[cache_key]
                if img_url:
                    # Display image from URL
                    img_placeholder.image(img_url, use_column_width=True)
                    # Show clickable link
                    img_placeholder.markdown(f"[🔗 원본 이미지 보기](https://unsplash.com/?utm_source=cakebot&utm_medium=referral)", unsafe_allow_html=True)
        
        # Right: Text description
        with col_right:
            st.markdown(f"### 🎨 {title}")
            st.markdown(desc)
            
            # Add expandable details if present
            if suggestion.get("details"):
                with st.expander("자세한 내용"):
                    st.markdown(suggestion.get("details"))
        
        st.markdown("---")


def render_main_interface() -> None:
    """Render the main chatbot interface with event and design selection."""
    st.title("🎨 디자인 트렌드 추천 챗봇")
    st.write(
        "이벤트를 선택하고 원하는 디자인 카테고리를 고르면, "
        "다양한 스타일과 국가별 트렌드를 반영한 디자인을 추천받을 수 있습니다!"
    )
    
    # Event and design selection
    col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
    
    with col1:
        event = st.selectbox(
            "📌 이벤트 선택",
            EVENTS,
            key="event_select"
        )
        # Extract clean event name
        event_clean = event.split(" ", 1)[-1] if " " in event else event
        st.session_state.event_type = event_clean
    
    with col2:
        selected_styles = st.multiselect(
            "🎯 디자인 카테고리 선택 (중복 가능)",
            list(DESIGN_CATEGORIES.keys()),
            default=["케이크"],
            key="design_styles_select"
        )
        st.session_state.design_styles = selected_styles
    
    with col3:
        selected_countries = st.multiselect(
            "🌍 참고할 국가/지역",
            COUNTRIES,
            default=["한국"],
            key="countries_select"
        )
    
    with col4:
        st.write("")
        st.write("")
        if st.button("🗑️ 초기화", use_container_width=True):
            st.session_state.messages = []
            st.session_state.last_assistant = ""
            st.session_state.generated_images = {}
    
    # Chat history (compact view)
    st.markdown("---")
    st.subheader("💬 대화 기록")
    for msg in st.session_state.messages[-4:]:
        if msg["role"] == "user":
            st.markdown(f"**👤 나:** {msg['content'][:100]}...")
        elif msg["role"] == "assistant":
            st.markdown(f"**🤖 챗봇:** {msg['content'][:100]}...")
    
    # User input form
    st.markdown("---")
    with st.form(key="input_form", clear_on_submit=True):
        user_input = st.text_input(
            "✍️ 추가 요청이나 세부사항을 입력하세요:",
            placeholder="예: 더 modern한 스타일로 해줘 / 북유럽 감성 포함해줘"
        )
        submitted = st.form_submit_button("전송 📤", use_container_width=True)
    
    if submitted and user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        # Build system prompt with selected options
        system_prompt = build_system_prompt(
            st.session_state.event_type or "이벤트",
            st.session_state.design_styles or ["케이크"],
            selected_countries or ["한국"]
        )
        
        api_messages = [{"role": "system", "content": system_prompt}]
        
        # Add user input context
        context = (
            f"이벤트: {st.session_state.event_type}\n"
            f"디자인 카테고리: {', '.join(st.session_state.design_styles)}\n"
            f"참고 국가: {', '.join(selected_countries)}\n"
            f"사용자 요청: {user_input}"
        )
        api_messages.append({"role": "user", "content": context})
        
        # Add previous conversation history
        for m in st.session_state.messages[-8:]:
            if m["role"] in ["user", "assistant"]:
                api_messages.append(m)
        
        api_key = get_api_key()
        if not api_key:
            st.error(
                "❌ OpenAI API 키가 없습니다. "
                "`.streamlit/secrets.toml`에 `OPENAI_API_KEY`를 설정해 주세요."
            )
            return
        
        client = create_openai_client(api_key)
        with st.spinner("✨ 다양한 디자인 추천을 생성 중입니다..."):
            assistant_reply = call_chat_api(
                client,
                api_messages,
                model="gpt-4o-mini"
            )
        
        st.session_state.messages.append({
            "role": "assistant",
            "content": assistant_reply
        })
        st.session_state.last_assistant = assistant_reply
        st.experimental_rerun()
    
    # Display suggestions as design cards with dual columns
    if st.session_state.last_assistant:
        st.markdown("---")
        st.subheader("🎨 추천 디자인 (자동 생성 이미지 포함)")
        
        suggestions = parse_suggestions(st.session_state.last_assistant)
        
        for i, suggestion in enumerate(suggestions):
            render_design_card(
                i,
                suggestion,
                get_api_key(),
                st.session_state.event_type or "이벤트",
                st.session_state.design_styles or ["케이크"]
            )
        
        # Baker summary section
        st.markdown("---")
        if st.button("👨‍🍳 제빵사 요약 보기"):
            api_key = get_api_key()
            client = create_openai_client(api_key)
            with st.spinner("제빵사가 요약을 작성 중입니다..."):
                sys = (
                    "당신은 친근한 제빵사 캐릭터입니다. "
                    "아래 디자인 추천 내용을 짧고 재미있게 요약해 주세요 (2-3문장). "
                    "이모지와 따뜻한 말투를 사용하세요."
                )
                messages = [
                    {"role": "system", "content": sys},
                    {"role": "user", "content": st.session_state.last_assistant},
                ]
                summary = call_chat_api(client, messages, model="gpt-4o-mini")
            st.info(f"👨‍🍳 {summary}")


def main():
    """Main application entry point."""
    init_session_state()
    
    if not get_api_key():
        st.error(
            "⚠️ OpenAI API 키가 설정되어 있지 않습니다.\n"
            "`.streamlit/secrets.toml`에 다음을 추가하세요:\n"
            "`OPENAI_API_KEY=\"your-api-key-here\"`"
        )
        st.stop()
    
    render_main_interface()


if __name__ == "__main__":
    main()


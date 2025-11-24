배포 가이드 — 디자인 트렌드 추천봇

이 저장소는 `streamlit_app.py` 단일 파일로 Streamlit 앱을 제공합니다. 아래는 여러 배포 옵션과 필요한 설정입니다.

중요: 절대 레포에 API 키를 평문으로 커밋하지 마세요. 현재 로컬에서 `.streamlit/secrets.toml`을 사용 중이라면 배포환경의 시크릿 설정에 동일 키를 추가하거나 환경변수로 설정하세요.

1) Streamlit Community Cloud (가장 쉬움)
- GitHub에 이 레포를 푸시하세요.
- https://share.streamlit.io 에 로그인 -> New app -> 레포 선택 -> 브랜치/경로 선택 -> Deploy
- App settings > Secrets에 `OPENAI_API_KEY` 키 추가 (값은 본인 키)

2) Render (간편, 무료 티어 있음)
- Render 웹사이트에서 New > Web Service > Connect GitHub repo 선택
- Build Command: `pip install -r requirements.txt`
- Start Command: `streamlit run streamlit_app.py --server.port $PORT --server.address 0.0.0.0`
- Environment > Add Secret `OPENAI_API_KEY`

3) Google Cloud Run (Docker 사용 권장)
- 로컬에서 Docker 이미지 빌드 및 테스트:
```bash
docker build -t my-cakebot .
docker run -e OPENAI_API_KEY="$OPENAI_API_KEY" -p 8080:8080 my-cakebot
```
- Cloud Build / Cloud Run으로 이미지 푸시 후 배포. 서비스의 환경변수에 `OPENAI_API_KEY` 설정.

4) 간단한 로컬 실행
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```

파일 요약
- `streamlit_app.py`: 앱 소스
- `requirements.txt`: 의존성(이미 포함되어야 함)
- `Dockerfile`: 컨테이너 배포용

문제가 발생하면 터미널 로그(전체 traceback)를 붙여 주세요. 배포 환경(예: Render/Cloud Run/Streamlit Cloud) 중 어느 곳에 배포할지 알려주시면 제가 필요한 환경 설정(예: CI, service file, cloud run deploy 명령)을 더 자세히 작성해 드립니다.

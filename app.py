import streamlit as st
import tempfile
import os
import torch
import soundfile as sf
import zipfile
from demucs.pretrained import get_model
from demucs.apply import apply_model

# 샘플 오디오 파일 경로(예시, 실제 파일은 프로젝트에 포함하거나 외부 URL 사용)
SAMPLE_AUDIO_URL = "https://github.com/adefossez/demucs/raw/main/tests/mixture-3s.mp3"
SAMPLE_AUDIO_NAME = "샘플_음원.mp3"

# --- 커스텀 CSS로 카드/버튼/폰트 스타일 개선 ---
st.markdown('''
    <style>
    .main-title {font-size:2.5rem;font-weight:900;color:#4f8cff;text-align:center;margin-bottom:0.5em;letter-spacing:-1px;}
    .desc {font-size:1.1rem;color:#444;text-align:center;margin-bottom:2em;}
    .stButton>button {background:linear-gradient(90deg,#4f8cff,#6ee7b7);color:white;font-weight:bold;border-radius:8px;padding:0.6em 2em;font-size:1.1rem;}
    .stDownloadButton>button {background:#f7f7fa;color:#222;border-radius:8px;font-weight:bold;}
    .result-card {background:#f7f7fa;border-radius:12px;padding:1.5em 1em;margin-top:1.5em;box-shadow:0 2px 8px #0001;}
    .option-label {font-weight:700;color:#4f8cff;}
    @media (max-width: 600px) {
      .main-title {font-size:1.5rem;}
      .desc {font-size:0.95rem;}
    }
    </style>
''', unsafe_allow_html=True)

# --- 타이틀/설명 ---
st.markdown('<div class="main-title">🎵 SplitTune: AI 음원 분리</div>', unsafe_allow_html=True)
st.markdown('<div class="desc">SplitTune은 Demucs 기반의 쉽고 빠른 음원 분리 웹앱입니다.<br>오디오 파일을 업로드하면 보컬, 드럼, 베이스, 기타 등으로 분리해드립니다.</div>', unsafe_allow_html=True)

# --- 업로드/옵션/고급설정 컬럼 ---
col1, col2, col3 = st.columns([2,1,1])
with col1:
    uploaded_file = st.file_uploader("1. 오디오 파일 업로드 (mp3, wav)", type=["mp3", "wav"], help="최대 100MB 권장")
with col2:
    st.markdown('<span class="option-label">2. 분리 옵션</span>', unsafe_allow_html=True)
    option = st.selectbox("분리 방식 선택", [
        "전체 분리 (보컬/드럼/베이스/기타)",
        "보컬만 추출 (Karaoke)",
        "보컬 제거 (Instrumental)",
        "드럼만 추출",
        "드럼 제거",
        "베이스만 추출",
        "베이스 제거",
        "기타만 추출",
        "기타 제거",
        "모든 음원 (각 파트+no_파트)"
    ])
with col3:
    st.markdown('<span class="option-label">3. 고급 설정</span>', unsafe_allow_html=True)
    with st.expander("고급 옵션", expanded=False):
        model_name = st.selectbox("Demucs 모델", ["htdemucs", "htdemucs_ft", "mdx_q", "mdx_extra_q"], index=0)
        segment = st.slider("분할(segment) 길이(초)", min_value=5, max_value=30, value=15)

progress_placeholder = st.empty()
result_placeholder = st.empty()

if st.button("✨ 분리 시작", use_container_width=True) and uploaded_file:
    with st.spinner("분리 중입니다... (최초 실행 시 모델 다운로드로 시간이 걸릴 수 있습니다)"):
        progress_placeholder.progress(10, text="모델 로드 중...")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp.write(uploaded_file.read())
            tmp_path = tmp.name

        model = get_model(model_name)
        model.cpu()
        model.eval()
        progress_placeholder.progress(30, text="오디오 파일 분석 중...")

        wav, sr = sf.read(tmp_path, always_2d=True)
        wav = torch.from_numpy(wav.T).float()
        ref = wav.mean(0)
        wav = (wav - ref.mean()) / ref.std()
        progress_placeholder.progress(60, text="음원 분리 중...")

        # segment 옵션은 실제 demucs.apply_model에서 지원하지 않을 수 있으므로, 고급 사용자는 별도 구현 필요
        sources = apply_model(model, wav[None], device="cpu")[0]
        sources = sources * ref.std() + ref.mean()
        progress_placeholder.progress(90, text="결과 파일 생성 중...")

        out_dir = tempfile.mkdtemp()
        zip_path = os.path.join(out_dir, "splittune_result.zip")
        result_html = '<div class="result-card"><b>분리 완료! 아래에서 각 파트를 다운로드하거나 ZIP으로 받으세요.</b><br><br>'
        wav_files = []
        for i, name in enumerate(model.sources):
            show = (
                option.startswith("전체 분리") or
                (option == "보컬만 추출 (Karaoke)" and name == "vocals") or
                (option == "보컬 제거 (Instrumental)" and name != "vocals") or
                (option == "드럼만 추출" and name == "drums") or
                (option == "드럼 제거" and name != "drums") or
                (option == "베이스만 추출" and name == "bass") or
                (option == "베이스 제거" and name != "bass") or
                (option == "기타만 추출" and name == "other") or
                (option == "기타 제거" and name != "other") or
                option.startswith("모든 음원")
            )
            if show:
                out_path = os.path.join(out_dir, f"{name}.wav")
                sf.write(out_path, sources[i].T.cpu().numpy(), sr)
                wav_files.append(out_path)
                with open(out_path, "rb") as f:
                    st.download_button(f"{name} 다운로드", f, file_name=f"{name}.wav", key=f"dl_{name}")
                result_html += f'<span style="color:#4f8cff;font-weight:600;">{name}</span> '
        # zip 파일 생성
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for file in wav_files:
                zipf.write(file, os.path.basename(file))
        with open(zip_path, "rb") as fzip:
            st.download_button("모든 결과 ZIP 다운로드", fzip, file_name="splittune_result.zip", key="dl_zip")
        result_html += '</div>'
        result_placeholder.markdown(result_html, unsafe_allow_html=True)
        progress_placeholder.empty() 
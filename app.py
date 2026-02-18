import streamlit as st
import os
import requests
import time
import base64
import json
from datetime import datetime
from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials

# Load environment variables
load_dotenv()

# Language mapping
AWARRI_LANGUAGE_MAPPING = {
    "hausa": "Hausa",
    "english": "English"
}

# Google Sheets setup
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

@st.cache_resource
def get_google_sheets_client():
    """Initialize Google Sheets client"""
    try:
        # Try to load from Streamlit secrets first (for deployment)
        if hasattr(st, 'secrets') and "GOOGLE_SHEETS_CREDENTIALS" in st.secrets:
            creds_dict = dict(st.secrets["GOOGLE_SHEETS_CREDENTIALS"])
        else:
            # Fallback to environment variable (for local development)
            creds_json = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
            if not creds_json:
                st.error("Google Sheets credentials not found")
                return None
            creds_dict = json.loads(creds_json)
        
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"Failed to initialize Google Sheets: {str(e)}")
        return None

def save_to_google_sheets(data):
    """Save evaluation data to Google Sheets"""
    try:
        client = get_google_sheets_client()
        if not client:
            return False
        
        # Try to get Sheet ID from secrets first (for deployment), then env (for local)
        sheet_id = st.secrets.get("GOOGLE_SHEET_ID") if hasattr(st, 'secrets') else os.getenv("GOOGLE_SHEET_ID")
        if not sheet_id:
            st.error("Google Sheet ID not found")
            return False
        
        spreadsheet = client.open_by_key(sheet_id)
        worksheet = spreadsheet.sheet1
        
        # Check if headers exist, if not add them
        try:
            headers = worksheet.row_values(1)
            if not headers:
                raise Exception("No headers")
        except:
            headers = [
                'Timestamp',
                'User Name',
                'Naturalness Score',
                'Accuracy Score',
                'Pronouncing Numbers Score',
                'Pronouncing MTN Lingo Score',
                'Overall Comment'
            ]
            worksheet.append_row(headers)
        
        # Append data
        row = [
            data['Timestamp'],
            data['User Name'],
            data['Naturalness Score'],
            data['Accuracy Score'],
            data['Pronouncing Numbers Score'],
            data['Pronouncing MTN Lingo Score'],
            data['Overall Comment']
        ]
        worksheet.append_row(row)
        return True
        
    except Exception as e:
        st.error(f"Failed to save to Google Sheets: {str(e)}")
        return False

def encode_audio_to_base64_uri(audio_bytes):
    """Encode audio bytes to base64 data URI"""
    base64_audio = base64.b64encode(audio_bytes).decode('utf-8')
    return f"data:audio/wav;base64,{base64_audio}"

def transcribe_with_awarri_new(audio_bytes, language):
    """Transcribe audio using new Awarri API"""
    try:
        base64_data_uri = encode_audio_to_base64_uri(audio_bytes)
        
        payload = {
            "base64Data": base64_data_uri,
            "language": AWARRI_LANGUAGE_MAPPING.get(language.lower(), "English")
        }
        
        headers = {
            "x-api-key": os.getenv("AWARRI_NEW_API_KEY"),
            "Content-Type": "application/json",
        }
        
        start_time = time.time()
        response = requests.post(
            "https://dev.langeasyllm.com/v1/asr/transcribe",
            json=payload,
            headers=headers,
            timeout=60
        )
        response.raise_for_status()
        latency = time.time() - start_time
        
        response_data = response.json()
        transcription = response_data.get("text", "")
        
        return {
            'transcription': transcription,
            'latency': round(latency, 2),
            'status': 'success'
        }
        
    except Exception as e:
        return {
            'transcription': f"Error: {str(e)}",
            'latency': 0.0,
            'status': 'error'
        }

def generate_awarri_audio(text: str):
    """
    Generate audio using the new Awarri TTS endpoint.
    Uses returnFormat='audio' (raw WAV bytes).
    Returns (audio_base64, latency)
    """
    url = os.getenv("AWARRI_TTS_URL")
    api_key = os.getenv("AWARRI_API_KEY")

    if not url or not api_key:
        st.error("Awarri API credentials not configured")
        return None, 0.0

    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/wav"
    }

    payload = {
        "text": text,
        "language": "Hausa",
        "returnFormat": "audio"
    }

    try:
        start_time = time.time()
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=60
        )
        latency = time.time() - start_time

        if response.status_code != 200:
            st.error("Awarri TTS request failed")
            st.code(
                f"Status: {response.status_code}\nResponse: {response.text}",
                language="text"
            )
            return None, latency

        audio_bytes = response.content
        audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")

        return audio_base64, latency

    except requests.exceptions.RequestException as e:
        st.error("Awarri TTS network error")
        st.code(str(e), language="text")
        return None, 0.0

def get_audio_files():
    """Get all audio files from the hausa_audio folder"""
    audio_folder = "hausa_audio"
    
    audio_files = {
        'short': [],
        'medium': [],
        'long': []
    }
    
    if os.path.exists(audio_folder):
        for i in range(1, 6):
            file_path = os.path.join(audio_folder, f"Hausa_short_audio{i}.wav")
            if os.path.exists(file_path):
                audio_files['short'].append(file_path)
        
        for i in range(1, 5):
            file_path = os.path.join(audio_folder, f"Hausa_medium_audio{i}.wav")
            if os.path.exists(file_path):
                audio_files['medium'].append(file_path)
        
        for i in range(1, 5):
            file_path = os.path.join(audio_folder, f"Hausa_long_audio{i}.wav")
            if os.path.exists(file_path):
                audio_files['long'].append(file_path)
    
    return audio_files

# Text data for reference
TEXTS = {
    'short': [
        "Sannu! Ta yaya zan iya taimaka maka yau?",
        "Don Allah jira ɗan lokaci.",
        "Ana sarrafa buƙatarka.",
        "Na gode da tuntuɓar MTN.",
        "Shigarwar ba daidai ba, don Allah gwada kuma."
    ],
    'medium': [
        "Adadin bayananka shi ne ₦600. Zai ƙare a ranar 20 ga Oktoba. Latsa *131# don siyan ƙari.",
        "Zan iya taimaka maka da airtime, data ko matsalar asusu. Me kake son yi?",
        "Kana da shirin bayanai guda ɗaya mai aiki yanzu. Kana so ka kalla ko ka soke shi?",
        "Yi hakuri, ban ji hakan ba. Za ka iya maimaitawa?"
    ],
    'long': [
        "Barka da zuwa MTN Sashen Kula da Abokan Hulɗa. Zaka iya siyan bayanai, cajar airtime, bincika balance ɗinka, ko neman taimako kan asusunka. Don Allah zaɓi zaɓi don ci gaba.",
        "Mun lura cewa ka yi amfani da kashi 80% na bayananka. Don guje wa katsewa, zaka iya ƙara bayananka ta *131# ko ta cikin MTN app.",
        "SIM ɗinka ba a gama rajista ba don wasu ayyuka. Don kammala, je cibiyar MTN mafi kusa tare da sahihin ID. Mun gode da fahimtarka.",
        "Airtime ɗinka bai isa kammala wannan mu'amala ba. Don Allah caji layinka sannan ka sake gwadawa. Latsa *555*PIN# don caji."
    ]
}

# Streamlit App
st.set_page_config(page_title="TTS Model Testing", layout="wide")

st.title("🎙️ TTS Model Testing Application")

# Create tabs
tab1, tab2 = st.tabs(["📊 Evaluate Previous Tests", "🔴 Live Test"])

# Tab 1: Evaluate Previous Tests
with tab1:
    st.header("Evaluate Previous TTS Tests")
    
    # Scoring criteria explanation
    with st.expander("ℹ️ Scoring Criteria Explanation", expanded=False):
        st.markdown("""
        **After listening to all audios, rate the overall TTS model on a scale of 1-10 for the following criteria:**
        
        1. **Naturalness (1-10)**: How natural and human-like does the audio sound? Does it have appropriate rhythm, intonation, and flow?
        
        2. **Accuracy (1-10)**: How accurately does the audio represent the original text? Are all words pronounced correctly?
        
        3. **Pronouncing Numbers (1-10)**: How well does the model pronounce numerical values (e.g., ₦600, 20, 80%, etc.)?
        
        4. **Pronouncing MTN Lingo (1-10)**: How well does the model pronounce MTN-specific terms and codes (e.g., Xtratime, *131#, *303#, *555*PIN#, etc.)?
        """)
    
    # User name input
    user_name = st.text_input("Enter Your Name", key="user_name")
    
    if not user_name:
        st.warning("⚠️ Please enter your name to begin evaluation.")
    else:
        audio_files = get_audio_files()
        
        if not any(audio_files.values()):
            st.error("❌ No audio files found in 'hausa_audio' folder. Please ensure audio files are present.")
        else:
            st.success(f"👤 Evaluator: **{user_name}**")
            st.info("👂 Listen to all audios below, then provide your overall evaluation at the bottom.")
            
            # Short audios
            st.subheader("📝 Short Audios")
            for idx, (audio_path, text) in enumerate(zip(audio_files['short'], TEXTS['short']), 1):
                with st.container():
                    st.markdown(f"**Audio {idx}**")
                    col1, col2 = st.columns([2, 3])
                    
                    with col1:
                        st.audio(audio_path)
                    
                    with col2:
                        st.text_area(f"Original Text", text, height=80, key=f"text_short_{idx}", disabled=True)
                    
                    st.divider()
            
            # Medium audios
            st.subheader("📄 Medium Audios")
            for idx, (audio_path, text) in enumerate(zip(audio_files['medium'], TEXTS['medium']), 1):
                with st.container():
                    st.markdown(f"**Audio {idx}**")
                    col1, col2 = st.columns([2, 3])
                    
                    with col1:
                        st.audio(audio_path)
                    
                    with col2:
                        st.text_area(f"Original Text", text, height=100, key=f"text_medium_{idx}", disabled=True)
                    
                    st.divider()
            
            # Long audios
            st.subheader("📋 Long Audios")
            for idx, (audio_path, text) in enumerate(zip(audio_files['long'], TEXTS['long']), 1):
                with st.container():
                    st.markdown(f"**Audio {idx}**")
                    col1, col2 = st.columns([2, 3])
                    
                    with col1:
                        st.audio(audio_path)
                    
                    with col2:
                        st.text_area(f"Original Text", text, height=120, key=f"text_long_{idx}", disabled=True)
                    
                    st.divider()
            
            # Overall evaluation section
            st.subheader("📝 Overall Evaluation")
            st.markdown("**After listening to all audios above, provide your overall scores:**")
            
            cols = st.columns(4)
            with cols[0]:
                naturalness = st.number_input("Naturalness (1-10)", 1, 10, 5, key="overall_naturalness")
            with cols[1]:
                accuracy = st.number_input("Accuracy (1-10)", 1, 10, 5, key="overall_accuracy")
            with cols[2]:
                numbers = st.number_input("Numbers (1-10)", 1, 10, 5, key="overall_numbers")
            with cols[3]:
                mtn = st.number_input("MTN Lingo (1-10)", 1, 10, 5, key="overall_mtn")
            
            # Overall comment
            st.subheader("💬 Overall Comment")
            overall_comment = st.text_area("Add any additional comments about your evaluation", height=150, key="overall_comment")
            
            # Submit button
            if st.button("📤 Submit Evaluation", type="primary"):
                if user_name:
                    with st.spinner("Saving evaluation to Google Sheets..."):
                        # Prepare data
                        data = {
                            'Timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            'User Name': user_name,
                            'Naturalness Score': naturalness,
                            'Accuracy Score': accuracy,
                            'Pronouncing Numbers Score': numbers,
                            'Pronouncing MTN Lingo Score': mtn,
                            'Overall Comment': overall_comment
                        }
                        
                        # Save to Google Sheets
                        if save_to_google_sheets(data):
                            st.success("✅ Evaluation submitted successfully to Google Sheets!")
                            st.balloons()
                        else:
                            st.error("❌ Failed to save evaluation. Please try again.")
                else:
                    st.error("❌ Please enter your name before submitting.")

# Tab 2: Live Test
with tab2:
    st.header("Live Audio Testing")
    st.write("Record audio and test the transcription model in real-time.")
    
    # Text input for TTS generation
    st.subheader("📝 Generate Audio from Text")
    text_input = st.text_area(
        "Enter Hausa text to convert to speech",
        height=120,
        placeholder="Type your Hausa text here...",
        key="tts_text_input"
    )
    
    if st.button("🎵 Generate Audio", type="primary"):
        if not text_input.strip():
            st.warning("⚠️ Please enter text before generating")
        else:
            with st.spinner("Generating audio with Awarri TTS..."):
                audio_base64, latency = generate_awarri_audio(text_input)
                if audio_base64:
                    st.success(f"✅ Audio generated in {latency:.2f}s")
                    
                    # Display the generated audio
                    audio_bytes = base64.b64decode(audio_base64)
                    st.audio(audio_bytes, format="audio/wav")
                    
                    # Store in session state for transcription testing
                    st.session_state.generated_audio = audio_bytes
    
    st.divider()
    
    # Audio recorder for transcription testing
    st.subheader("🎤 Test Transcription")
    audio_bytes = st.audio_input("Record your audio")
    
    if audio_bytes:
        st.audio(audio_bytes, format="audio/wav")
        
        language = st.selectbox("Select Language", ["Hausa", "English"], key="live_language")
        
        if st.button("📝 Transcribe Audio", type="primary"):
            with st.spinner("Transcribing..."):
                result = transcribe_with_awarri_new(audio_bytes.getvalue(), language)
                
                if result['status'] == 'success':
                    st.success("✅ Transcription Complete!")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Latency", f"{result['latency']} seconds")
                    with col2:
                        st.metric("Status", result['status'].upper())
                    
                    st.subheader("Transcription:")
                    st.write(result['transcription'])
                else:
                    st.error(f"❌ Transcription Failed: {result['transcription']}")

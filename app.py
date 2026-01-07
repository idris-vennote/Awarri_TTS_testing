import streamlit as st
import os
import requests
import time
import base64
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Language mapping
AWARRI_LANGUAGE_MAPPING = {
    "hausa": "Hausa",
    "english": "English"
}

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
            "https://vennote.langeasyllm.com/v1/asr/transcribe",
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

def save_to_excel(data, filename="tts_evaluation_scores.xlsx"):
    """Save or append evaluation data to Excel file"""
    df_new = pd.DataFrame([data])
    
    if os.path.exists(filename):
        df_existing = pd.read_excel(filename)
        df_combined = pd.concat([df_existing, df_new], ignore_index=True)
        df_combined.to_excel(filename, index=False)
    else:
        df_new.to_excel(filename, index=False)

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

# Create tabs - SWAPPED ORDER
tab1, tab2 = st.tabs(["📊 Evaluate Previous Tests", "🔴 Live Test"])

# Tab 1: Evaluate Previous Tests (NOW FIRST)
with tab1:
    st.header("Evaluate Previous TTS Tests")
    
    # Scoring criteria explanation
    with st.expander("ℹ️ Scoring Criteria Explanation", expanded=False):
        st.markdown("""
        **Rate each audio on a scale of 1-10 for the following criteria:**
        
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
            
            # Store scores
            if 'scores' not in st.session_state:
                st.session_state.scores = {}
            
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
                    
                    # Scoring inputs
                    cols = st.columns(4)
                    audio_name = f"Hausa_short_audio{idx}"
                    
                    with cols[0]:
                        naturalness = st.number_input("Naturalness", 1, 10, 5, key=f"nat_short_{idx}")
                    with cols[1]:
                        accuracy = st.number_input("Accuracy", 1, 10, 5, key=f"acc_short_{idx}")
                    with cols[2]:
                        numbers = st.number_input("Numbers", 1, 10, 5, key=f"num_short_{idx}")
                    with cols[3]:
                        mtn = st.number_input("MTN Lingo", 1, 10, 5, key=f"mtn_short_{idx}")
                    
                    st.session_state.scores[audio_name] = {
                        'naturalness': naturalness,
                        'accuracy': accuracy,
                        'numbers': numbers,
                        'mtn_lingo': mtn
                    }
                    
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
                    
                    # Scoring inputs
                    cols = st.columns(4)
                    audio_name = f"Hausa_medium_audio{idx}"
                    
                    with cols[0]:
                        naturalness = st.number_input("Naturalness", 1, 10, 5, key=f"nat_medium_{idx}")
                    with cols[1]:
                        accuracy = st.number_input("Accuracy", 1, 10, 5, key=f"acc_medium_{idx}")
                    with cols[2]:
                        numbers = st.number_input("Numbers", 1, 10, 5, key=f"num_medium_{idx}")
                    with cols[3]:
                        mtn = st.number_input("MTN Lingo", 1, 10, 5, key=f"mtn_medium_{idx}")
                    
                    st.session_state.scores[audio_name] = {
                        'naturalness': naturalness,
                        'accuracy': accuracy,
                        'numbers': numbers,
                        'mtn_lingo': mtn
                    }
                    
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
                    
                    # Scoring inputs
                    cols = st.columns(4)
                    audio_name = f"Hausa_long_audio{idx}"
                    
                    with cols[0]:
                        naturalness = st.number_input("Naturalness", 1, 10, 5, key=f"nat_long_{idx}")
                    with cols[1]:
                        accuracy = st.number_input("Accuracy", 1, 10, 5, key=f"acc_long_{idx}")
                    with cols[2]:
                        numbers = st.number_input("Numbers", 1, 10, 5, key=f"num_long_{idx}")
                    with cols[3]:
                        mtn = st.number_input("MTN Lingo", 1, 10, 5, key=f"mtn_long_{idx}")
                    
                    st.session_state.scores[audio_name] = {
                        'naturalness': naturalness,
                        'accuracy': accuracy,
                        'numbers': numbers,
                        'mtn_lingo': mtn
                    }
                    
                    st.divider()
            
            # Overall comment
            st.subheader("💬 Overall Comment")
            overall_comment = st.text_area("Add any additional comments about your evaluation", height=150, key="overall_comment")
            
            # Submit button
            if st.button("📤 Submit Evaluation", type="primary"):
                if user_name:
                    with st.spinner("Saving evaluation..."):
                        # Save all scores to Excel
                        for audio_name, scores in st.session_state.scores.items():
                            data = {
                                'Timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                'User Name': user_name,
                                'Audio Name': audio_name,
                                'Naturalness Score': scores['naturalness'],
                                'Accuracy Score': scores['accuracy'],
                                'Pronouncing Numbers Score': scores['numbers'],
                                'Pronouncing MTN Lingo Score': scores['mtn_lingo'],
                                'Overall Comment': overall_comment
                            }
                            save_to_excel(data)
                        
                        st.success("✅ Evaluation submitted successfully!")
                        st.balloons()
                else:
                    st.error("❌ Please enter your name before submitting.")

# Tab 2: Live Test (NOW SECOND)
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
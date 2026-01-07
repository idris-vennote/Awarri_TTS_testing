import os
import time
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ==============================
# CONFIG
# ==============================
TTS_URL = os.getenv("AWARRI_TTS_URL")  # same as Streamlit
API_KEY = os.getenv("AWARRI_API_KEY")

OUTPUT_DIR = Path("hausa_audio")
OUTPUT_DIR.mkdir(exist_ok=True)

HEADERS = {
    "x-api-key": API_KEY,
    "Content-Type": "application/json",
    "Accept": "audio/wav"
}

# ==============================
# HAUSA TEXT DATA
# ==============================
TEXTS = {
    "short": [
        "Sannu! Ta yaya zan iya taimaka maka yau?",
        "Don Allah jira ɗan lokaci.",
        "Ana sarrafa buƙatarka.",
        "Na gode da tuntuɓar MTN.",
        "Shigarwar ba daidai ba, don Allah gwada kuma."
    ],
    "medium": [
        "Adadin bayananka shi ne ₦600. Zai ƙare a ranar 20 ga Oktoba. Latsa *131# don siyan ƙari.",
        "Zan iya taimaka maka da airtime, data ko matsalar asusu. Me kake son yi?",
        "Kana da shirin bayanai guda ɗaya mai aiki yanzu. Kana so ka kalla ko ka soke shi?",
        "Yi hakuri, ban ji hakan ba. Za ka iya maimaitawa?"
    ],
    "long": [
        "Barka da zuwa MTN Sashen Kula da Abokan Hulɗa. Zaka iya siyan bayanai, cajar airtime, bincika balance ɗinka, ko neman taimako kan asusunka. Don Allah zaɓi zaɓi don ci gaba.",
        "Mun lura cewa ka yi amfani da kashi 80% na bayananka. Don guje wa katsewa, zaka iya ƙara bayananka ta *131# ko ta cikin MTN app.",
        "SIM ɗinka ba a gama rajista ba don wasu ayyuka. Don kammala, je cibiyar MTN mafi kusa tare da sahihin ID. Mun gode da fahimtarka.",
        "Airtime ɗinka bai isa kammala wannan mu'amala ba. Don Allah caji layinka sannan ka sake gwadawa. Latsa *555*PIN# don caji."
    ]
}

# ==============================
# TTS FUNCTION (EXACT MATCH)
# ==============================
def synthesize_awarri_tts(text: str) -> bytes:
    payload = {
        "text": text,
        "language": "Hausa",
        "returnFormat": "audio"
    }

    response = requests.post(
        TTS_URL,
        headers=HEADERS,
        json=payload,
        timeout=60
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"Awarri TTS failed ({response.status_code}): {response.text}"
        )

    return response.content  # 🔑 RAW WAV BYTES

# ==============================
# MAIN LOOP
# ==============================
def run_batch_tts():
    for category, texts in TEXTS.items():
        for idx, text in enumerate(texts, start=1):
            filename = f"Hausa_{category}_audio{idx}.wav"
            output_path = OUTPUT_DIR / filename

            print(f"Generating: {filename}")
            start = time.time()

            audio_bytes = synthesize_awarri_tts(text)
            with open(output_path, "wb") as f:
                f.write(audio_bytes)

            print(f"Saved ({time.time() - start:.2f}s)")

    print("\n✅ All Hausa audio files generated successfully.")

# ==============================
# ENTRY POINT
# ==============================
if __name__ == "__main__":
    run_batch_tts()

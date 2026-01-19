# AI-Powered Legal Discovery Assistant

A Streamlit application designed for the **ElevenLabs Scribe v2 Hackathon**. This tool leverages ElevenLabs' advanced speech recognition to transcribe legal audio evidence, featuring keyterm prompting and entity detection.

## Features
- **Scribe v2 Integration**: High-accuracy transcription with `transcription_hints`.
- **Entity Detection**: Automatically identifies people, dates, contract terms, etc.
- **Secure**: API keys are transient and never stored.
- **Export**: Download results as txt, JSON, or professional PDF reports.

## Setup & Run

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the App**
   ```bash
   streamlit run app.py
   ```

## Deployment
Ready for deployment on [Streamlit Community Cloud](https://streamlit.io/cloud). Just connect this repository!

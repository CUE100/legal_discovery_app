# AI-Powered Legal Discovery Assistant

A professional Streamlit application leveraging **ElevenLabs Scribe v2** for high-accuracy legal transcription. This tool is designed to process audio evidence with advanced features like speaker diarization, entity detection, and keyterm prompting.

## Features
- **Scribe v2 Integration**: High-accuracy transcription with `keyterms` support.
- **Smart Diarization**: Multi-speaker labeling for clear legal transcripts.
- **Entity Detection**: Automatically identifies people, dates, organizations, and legal terms.
- **Secure Architecture**: API keys are transient and stored only in session state.
- **Reporting**: Export results to TXT, JSON, or professional PDF reports.

## Setup & Run

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the App**
   ```bash
   streamlit run app.py
   ```

## Note for Free Tier Users
ElevenLabs may restrict usage on their Free Tier (Error 401: Unusual Activity). For production-grade stability and to bypass IP blocks, a paid subscription (Starter or higher) is recommended.


# Dependencies: pip install streamlit elevenlabs python-dotenv fpdf
# Run: streamlit run app.py

import streamlit as st
import os
import tempfile
import json
from fpdf import FPDF
from elevenlabs.client import ElevenLabs
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- Page Config ---
st.set_page_config(
    page_title="AI-Powered Legal Discovery Assistant",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Session State Initialization ---
if "api_key" not in st.session_state:
    st.session_state.api_key = ""
if "processed_results" not in st.session_state:
    st.session_state.processed_results = []


# --- Custom Styling ---
st.markdown("""
<style>
    .reportview-container {
        background: #f5f7f9;
    }
    .main-header {
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        color: #2c3e50;
    }
    .entity-tag {
        background-color: #e8f0fe;
        color: #1967d2;
        padding: 2px 6px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.9em;
        margin: 0 2px;
    }
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# --- Helper Functions ---

def generate_pdf(results):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    for res in results:
        pdf.add_page()
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, f"Transcript Report: {res['filename']}", ln=True)
        pdf.ln(5)
        
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "Summary of Entities:", ln=True)
        pdf.set_font("Arial", "", 11)
        
        # Simple summary of entities
        entity_counts = {}
        for entity in res.get('entities', []):
            e_type = entity.get('type', 'Unknown')
            entity_counts[e_type] = entity_counts.get(e_type, 0) + 1
            
        for e_type, count in entity_counts.items():
            pdf.cell(0, 8, f"- {e_type}: {count}", ln=True)
        
        pdf.ln(5)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "Full Transcript:", ln=True)
        pdf.set_font("Arial", "", 10)
        
        # Add text - handle latin-1 encoding issues common in FPDF by replacement
        text = res.get('text', '')
        text = text.encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 6, text)
        
    return pdf.output(dest='S').encode('latin-1')



def format_diarized_transcript(words):
    """Reconstructs transcript with speaker labels from word-level data."""
    if not words:
        return ""
    
    transcript_lines = []
    current_speaker = None
    current_text_chunk = []
    
    for word in words:
        # SDK word object typically has .text and .speaker_id
        # Fallback for dict access if it's a raw dict
        text = getattr(word, 'text', word.get('text', ''))
        speaker = getattr(word, 'speaker_id', word.get('speaker_id', 'Unknown'))
        
        # Audio events might come as words or separate logic, usually embedded in text or as types
        # Scribe v2 might put [laughter] as text.
        
        if speaker != current_speaker:
            if current_speaker is not None:
                # Flush previous
                label = current_speaker.replace('_', ' ').title()
                content = " ".join(current_text_chunk)
                transcript_lines.append(f"**{label}**: {content}")
            
            current_speaker = speaker
            current_text_chunk = [text]
        else:
            current_text_chunk.append(text)
            
    # Flush last
    if current_speaker is not None:
        label = current_speaker.replace('_', ' ').title()
        content = " ".join(current_text_chunk)
        transcript_lines.append(f"**{label}**: {content}")
        
    return "\n\n".join(transcript_lines)

def format_transcript_display(text, entities):
    """Formats transcript with highlighted entities for UI."""
    formatted_text = text
    
    # Simple entity highlighting
    if entities:
        # Sort entities by length (descending) to avoid partial replacements issues
        # e.g. replacing 'John' inside 'John Smith'
        # A robust way to handle entity highlighting:
        unique_entities = {e.get('text'): e.get('type') for e in entities if e.get('text')}
        sorted_entities = sorted(unique_entities.keys(), key=len, reverse=True)
        
        for e_text in sorted_entities:
            e_type = unique_entities[e_text]
            replacement = f"<span class='entity-tag' title='{e_type}'>{e_text}</span>"
            formatted_text = formatted_text.replace(e_text, replacement)
    
    # Convert newlines to HTML breaks if they aren't already formatted (Diarized text has markdown **)
    # We'll treat double newlines as paragraph breaks
    formatted_text = formatted_text.replace("\n\n", "<br><br>").replace("\n", "<br>")
    
    return formatted_text

# --- Sidebar ---
with st.sidebar:
    st.image("https://avatars.githubusercontent.com/u/100950301?s=200&v=4", width=80)
    st.title("Settings")
    
    api_key_input = st.text_input(
        "ElevenLabs API Key", 
        type="password", 
        help="Enter your ElevenLabs API Key. It is not saved permanently."
    )
    
    if api_key_input:
        st.session_state.api_key = api_key_input
        st.success("API Key provided")
    else:
        st.warning("Please enter your ElevenLabs API Key to proceed.")
            
    st.markdown("---")
    st.markdown("### About")
    st.info(
        "This tool uses **ElevenLabs Scribe v2** for high-accuracy legal transcription, "
        "featuring specific **Keyterm Prompting** and **Entity Detection**."
    )

# --- Main Page ---
st.title("⚖️ AI-Powered Legal Discovery Assistant")
st.markdown("### Supports Scribe v2 • Keyterm Prompting • Entity Detection")

# Input Section
col1, col2 = st.columns([2, 1])

with col1:
    uploaded_files = st.file_uploader(
        "Upload Audio Evidence (MP3, WAV)", 
        type=['mp3', 'wav'], 
        accept_multiple_files=True
    )

with col2:
    keyterms_input = st.text_area(
        "Keyterms / Transcription Hints", 
        placeholder="E.g., negligence, habeas corpus, Plaintiff Doe, NDA",
        help="Comma-separated list of terms to guide the AI transcription."
    )

process_btn = st.button("Analyze & Transcribe", disabled=not uploaded_files)

# --- Processing Logic ---

if process_btn:
    if not st.session_state.api_key:
        st.error("Please provide an ElevenLabs API Key in the sidebar to proceed.")
    else:
        st.session_state.processed_results = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Prepare hints
        hints = [term.strip() for term in keyterms_input.split(',')] if keyterms_input else []
        
        files_to_process = uploaded_files[:5] # Limit batch size for performance
        total_files = len(files_to_process)
        
        for i, uploaded_file in enumerate(files_to_process):
            status_text.text(f"Processing {uploaded_file.name} ({i+1}/{total_files})...")
            
            try:
                # Initialize Client
                client = ElevenLabs(api_key=st.session_state.api_key)
                
                # Save to temp file because SDK often needs a path or file-like object
                # Streamlit UploadedFile is file-like, but let's be safe with temp
                with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_path = tmp_file.name
                
                # Call Scribe v2
                # We use the 'scribe_v2' model and requested parameters
                with open(tmp_path, 'rb') as audio_file:
                    transcription = client.speech_to_text.convert(
                        file=audio_file,
                        model_id="scribe_v2", 
                        tag_audio_events=True, # Enable audio event tagging
                        language_code="en",
                        keyterms=hints,
                        entity_detection="all", # Supported by Scribe v2
                        diarize=True
                    )
                
                os.unlink(tmp_path) # Clean up
                
                # Parse Result
                # Try to get diarized text if available
                raw_text = getattr(transcription, 'text', str(transcription))
                formatted_transcript = raw_text
                
                words = getattr(transcription, 'words', [])
                if words:
                     diarized_text = format_diarized_transcript(words)
                     if diarized_text:
                         formatted_transcript = diarized_text
                
                result_data = {
                    "filename": uploaded_file.name,
                    "text": formatted_transcript,
                    "entities": [], # Populate if available in response
                    "status": "success"
                }
                
                # Attempt to extract entities if available in the raw response or attributes
                # For v2, entities might be in a specific property. 
                # If SDK logic varies, we default to empty list to avoid crash.
                if hasattr(transcription, 'entities'):
                        result_data['entities'] = [
                            {'text': e.text, 'type': e.type} for e in transcription.entities
                        ]
                
                st.session_state.processed_results.append(result_data)
                
            except Exception as e:
                st.error(f"Error processing {uploaded_file.name}: {str(e)}")
            
            progress_bar.progress((i + 1) / total_files)
        
        status_text.text("Processing Complete!")
        progress_bar.empty()

# --- Results Display ---

if st.session_state.processed_results:
    st.divider()
    st.subheader("Discovery Results")
    
    # Export All Buttons
    col_exp1, col_exp2, col_exp3 = st.columns(3)
    
    # helper for downloads
    all_text = "\n\n".join([f"--- {r['filename']} ---\n{r.get('text','')}" for r in st.session_state.processed_results])
    all_json = json.dumps(st.session_state.processed_results, indent=2)
    pdf_bytes = generate_pdf(st.session_state.processed_results)
    
    with col_exp1:
        st.download_button("Download All TXT", all_text, "transcripts.txt", "text/plain")
    with col_exp2:
        st.download_button("Download JSON Report", all_json, "discovery_report.json", "application/json")
    with col_exp3:
        st.download_button("Download PDF Report", pdf_bytes, "discovery_report.pdf", "application/pdf")
    
    st.markdown("---")

    # Individual File Details
    for res in st.session_state.processed_results:
        with st.expander(f"📄 {res['filename']}", expanded=True):
            
            # 1. Summary Metrics
            entities = res.get('entities', [])
            e_count = len(entities)
            
            m1, m2 = st.columns(2)
            m1.metric("Status", "Completed", delta="Success", delta_color="normal")
            m2.metric("Entities Detected", e_count)
            
            # 2. Tabs for different views
            tab1, tab2 = st.tabs(["📝 Tagged Transcript", "📊 Entity Data"])
            
            with tab1:
                formatted_html = format_transcript_display(res.get('text', ''), entities)
                st.markdown(f"<div style='background: white; padding: 20px; border-radius: 10px; border: 1px solid #ddd; line-height: 1.6;'>{formatted_html}</div>", unsafe_allow_html=True)
            
            with tab2:
                if entities:
                    st.json(entities)
                else:
                    st.info("No entities detected.")

# --- Footer ---
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666; font-size: 0.8em; padding: 20px;'>
        Powered by <b>ElevenLabs Scribe v2</b>.<br>
        High-accuracy legal transcription with Keyterm Prompting and Entity Detection.<br>
        Secure API Key usage.
    </div>
    """, 
    unsafe_allow_html=True
)

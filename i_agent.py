import os
import streamlit as st
import google.generativeai as genai
from dotenv import load_dotenv
import google.generativeai as genai
from dotenv import load_dotenv
import os

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

print("Available models:")
for m in genai.list_models():
    print(f"\nName: {m.name}")
    print(f"Description: {m.description}")
    print(f"Supported methods: {m.supported_generation_methods}")
# Set page config
st.set_page_config(
    page_title="AI Story Generator",
    page_icon="📖",
    layout="centered"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .main {
        max-width: 800px;
        padding: 2rem;
    }
    .title {
        font-size: 2.5rem;
        text-align: center;
        margin-bottom: 2rem;
        color: #1E88E5;
    }
    .story-box {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    }
    .stButton>button {
        width: 100%;
        background-color: #1E88E5;
        color: white;
        font-weight: bold;
        padding: 0.75rem;
        border-radius: 5px;
        border: none;
    }
    .stButton>button:hover {
        background-color: #1565C0;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if 'story' not in st.session_state:
    st.session_state.story = None

# Load environment variables
load_dotenv()

# Set up API key
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    st.error("🔑 Error: GOOGLE_API_KEY not found in .env file")
    st.stop()


# Configure the Gemini model
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash-lite')

def generate_story(prompt):
    try:
        # Create a more detailed prompt for better results
        full_prompt = f"""Write a creative short story based on the following prompt:
        
        {prompt}
        
        The story should be 3-5 paragraphs long, with engaging characters and a clear narrative arc. 
        Include vivid descriptions and dialogue where appropriate."""
        
        # Generate the story using bidiGenerateContent
        response = model.generate_content(full_prompt, stream=True)
        
        # Collect the response chunks
        story_chunks = []
        for chunk in response:
            if hasattr(chunk, 'text'):
                story_chunks.append(chunk.text)
        
        # Combine all chunks into a single string
        return "".join(story_chunks) if story_chunks else "No story was generated."
            
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        return None


# Streamlit UI
st.markdown('<h1 class="title">📖 AI Story Generator</h1>', unsafe_allow_html=True)

with st.form("story_form"):
    prompt = st.text_area(
        "Enter your story prompt:",
        placeholder="Example: A story about a robot who learns to love music...",
        height=100
    )
    
    submit_button = st.form_submit_button("Generate Story")

if submit_button and prompt:
    with st.spinner('✨ Crafting your story... This may take a moment.'):
        story = generate_story(prompt)
        st.session_state.story = story

if st.session_state.story:
    st.markdown("### Your Generated Story")
    st.markdown(f'<div class="story-box">{st.session_state.story}</div>', unsafe_allow_html=True)
    
    # Add a download button
    st.download_button(
        label="📥 Download Story",
        data=st.session_state.story,
        file_name="generated_story.txt",
        mime="text/plain"
    )
Running Kaggle 2025 AI course first AI agent and your first multi-agent system, using Agent Development Kit (ADK), powered by Gemini, and giving it the ability to use Google Search to answer questions with up-to-date information. 
In the second codelab,  multi-agent systems, to create teams of specialized agents and explore different architectural patterns.
# AI Story Generator

A Streamlit web application that generates creative short stories using Google's Gemini AI model.

## Features

- Generate creative short stories based on user prompts
- Clean and responsive web interface
- Download stories as text files
- Real-time story generation with loading indicators

## Prerequisites

- Python 3.8+
- Google API key with access to Gemini models
- Python packages listed in `requirements.txt`

## Installation

1. Clone the repository:
   ```bash
   git clone [https://github.com/SahSanjeev/Kaggle2025day1.git](https://github.com/SahSanjeev/Kaggle2025day1.git)
   cd Kaggle2025day1


   python -m venv .venv
.venv\Scripts\activate  # On Windows
# or
source .venv/bin/activate  # On macOS/Linux

GOOGLE_API_KEY=your_api_key_here

Usage
Run the Streamlit app:
bash
streamlit run i_agent.py
Open your web browser and navigate to http://localhost:8501
Enter a story prompt in the text area and click "Generate Story"
Once generated, you can read the story in the app or download it as a text file
Project Structure
i_agent.py
 - Main Streamlit application
.env - Environment variables (not version controlled)
requirements.txt - Python dependencies
License
This project is licensed under the MIT License - see the LICENSE file for details.

Acknowledgements
Google Gemini API
Streamlit

### Additional Recommendations:

1. **Create a `.gitignore` file** to exclude sensitive files:
.env pycache/ .venv/ .pyc .DS_Store


2. **Create a `requirements.txt`** with the necessary dependencies:
streamlit>=1.24.0 google-generativeai>=0.3.0 python-dotenv>=0.19.0

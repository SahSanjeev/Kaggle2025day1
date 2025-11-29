import os
import re
import asyncio
import textwrap
from datetime import datetime
from dotenv import load_dotenv
from typing import Dict, Any
from fpdf import FPDF

def save_to_pdf(query: str, response: str, output_dir: str = 'output_pdfs') -> str:
    """Save the query and response to a PDF file.
    
    Args:
        query: The user's query
        response: The AI's response
        output_dir: Directory to save the PDFs (default: 'output_pdfs')
        
    Returns:
        str: Path to the saved PDF file
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Create a sanitized filename from the query
    safe_query = "".join(c if c.isalnum() or c in ' _-' else '_' for c in query)
    safe_query = safe_query[:50]  # Limit filename length
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{output_dir}/response_{timestamp}_{safe_query}.pdf"
    
    # Create PDF
    pdf = FPDF()
    pdf.add_page()
    
    # Set font and colors
    pdf.set_font("Arial", 'B', 16)
    pdf.set_text_color(0, 0, 128)  # Dark blue for title
    
    # Add title
    pdf.cell(0, 10, "Query Response", 0, 1, 'C')
    pdf.ln(10)
    
    # Add query section
    pdf.set_font("Arial", 'B', 12)
    pdf.set_text_color(0, 0, 0)  # Black for text
    pdf.cell(0, 10, "Your Question:", 0, 1)
    pdf.set_font("Arial", '', 11)
    pdf.multi_cell(0, 7, query)
    pdf.ln(5)
    
    # Add response section
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "Response:", 0, 1)
    pdf.set_font("Arial", '', 11)
    
    # Process response text for PDF
    def clean_text(text):
        # Remove any HTML tags and extra whitespace
        text = re.sub(r'<[^>]+>', '', str(text))  # Remove HTML tags
        text = ' '.join(text.split())  # Normalize whitespace
        return text.strip()
    
    def split_into_sentences(text):
        # Simple sentence splitter that handles common cases
        text = clean_text(text)
        # Split on sentence endings followed by space and capital letter
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def format_paragraph(text, max_line_length=80):
        # Format text into lines of max_line_length, keeping words intact
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            if len(' '.join(current_line + [word])) <= max_line_length:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
        
        if current_line:
            lines.append(' '.join(current_line))
            
        return '\n'.join(lines)
    
    # Process the response text to extract clean content
    def extract_text_from_response(response_obj):
        """Extract clean text from various response formats."""
        def extract_text(obj):
            """Recursively extract text from nested objects."""
            if isinstance(obj, str):
                return obj.strip()
            elif hasattr(obj, 'text'):
                return str(obj.text).strip()
            elif hasattr(obj, 'parts'):
                return '\n\n'.join(filter(None, [extract_text(part) for part in obj.parts]))
            elif hasattr(obj, 'content') and hasattr(obj.content, 'parts'):
                return extract_text(obj.content)
            elif isinstance(obj, (list, tuple)):
                return '\n\n'.join(filter(None, [extract_text(item) for item in obj]))
            elif hasattr(obj, '__dict__'):
                # Try to find any text in the object's attributes
                for attr in ['text', 'content', 'parts']:
                    if hasattr(obj, attr):
                        result = extract_text(getattr(obj, attr))
                        if result:
                            return result
            return str(obj).strip()

        try:
            # First try to extract text using the recursive function
            text = extract_text(response_obj)
            
            # Clean up common artifacts
            text = re.sub(r'\[.*?\]', '', text)  # Remove anything in square brackets
            text = re.sub(r'<[^>]+>', '', text)    # Remove HTML tags
            text = re.sub(r'\s+', ' ', text)       # Normalize whitespace
            text = text.strip()
            
            # If we still have what looks like a Python repr, try to extract just the text parts
            if 'text=' in text and 'parts=' in text:
                # Try to extract text between text='...' or text="..." patterns
                text_parts = []
                # Handle single-quoted text
                text_parts.extend(re.findall(r"text='([^']+)'", text))
                # Handle double-quoted text
                text_parts.extend(re.findall(r'text="([^"]+)"', text))
                if text_parts:
                    text = '\n\n'.join(text_parts)
            
            return text if text else "No text content found in response"
            
        except Exception as e:
            print(f"Warning: Could not extract text from response: {str(e)}")
            return str(response_obj).strip()
    
    # Get clean text from the response
    response_text = extract_text_from_response(response)
    
    # Try to split into paragraphs first
    paragraphs = [p.strip() for p in response_text.split('\n\n') if p.strip()]
    
    # If no paragraphs found, try to split by sentences
    if not paragraphs or len(paragraphs) == 1 and len(paragraphs[0]) > 500:
        sentences = split_into_sentences(response_text)
        paragraphs = []
        current_para = []
        
        for sentence in sentences:
            current_para.append(sentence)
            # Start new paragraph after 3-5 sentences
            if len(current_para) >= 3 and (len(sentence) > 50 or len(' '.join(current_para)) > 200):
                paragraphs.append(' '.join(current_para))
                current_para = []
        
        if current_para:  # Add any remaining sentences
            paragraphs.append(' '.join(current_para))
    
    # Add content to PDF with better error handling
    def add_paragraph(pdf, text, font_size=11):
        """Safely add a paragraph to the PDF with error handling."""
        try:
            # Clean and format the text
            clean_para = ' '.join(str(text).split())  # Normalize whitespace
            if not clean_para.strip():
                pdf.ln(5)
                return
                
            # Set font
            pdf.set_font("Arial", '', font_size)
            
            # Split into lines that fit the page width
            lines = []
            current_line = []
            max_width = 190  # Max width in mm (A4 width - margins)
            
            for word in clean_para.split():
                # Check if adding this word would exceed the line width
                test_line = ' '.join(current_line + [word])
                if pdf.get_string_width(test_line) < max_width:
                    current_line.append(word)
                else:
                    if current_line:
                        lines.append(' '.join(current_line))
                    current_line = [word]
            
            if current_line:  # Add the last line
                lines.append(' '.join(current_line))
            
            # Add the lines to the PDF
            for line in lines:
                pdf.multi_cell(0, 7, line)
                
            pdf.ln(5)  # Add space after paragraph
            
        except Exception as e:
            print(f"Warning: Could not add text to PDF: {str(e)[:100]}...")
    
    # Add the response content with better formatting
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "Response:", 0, 1)
    pdf.set_font("Arial", '', 11)
    
    # Process each paragraph
    if not paragraphs:
        # If no paragraphs found, try to get the text directly
        direct_text = str(response).strip()
        if direct_text:
            add_paragraph(pdf, direct_text)
    else:
        for para in paragraphs:
            if para.strip():  # Only add non-empty paragraphs
                add_paragraph(pdf, para)
    
    # Add footer
    pdf.set_y(-15)
    pdf.set_font("Arial", 'I', 8)
    pdf.set_text_color(128, 128, 128)  # Gray for footer
    pdf.cell(0, 10, f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 0, 0, 'C')
    
    # Save the PDF
    pdf.output(filename)
    return filename

# Configure logging
print("=" * 80)
print(f"Script started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("-" * 80)

def load_environment() -> str:
    """Load environment variables and return the API key."""
    try:
        load_dotenv()
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found in .env file")
        os.environ["GOOGLE_API_KEY"] = api_key
        print("✅ Environment variables loaded successfully")
        return api_key
    except Exception as e:
        print(f"❌ Error loading environment: {e}")
        raise

def setup_agent() -> Any:  # Return type should be google.adk.agents.Agent
    """Set up and return the Google ADK agent."""
    try:
        from google.adk.agents import Agent
        from google.adk.models.google_llm import Gemini
        from google.adk.tools import google_search
        from google.genai import types
        
        # Configure retry options
        retry_config = types.HttpRetryOptions(
            attempts=5,
            exp_base=7,
            initial_delay=1,
            http_status_codes=[429, 500, 503, 504]
        )
        
        # Create the agent
        agent = Agent(
            name="helpful_assistant",
            model=Gemini(
                model="gemini-2.5-flash-lite",
                retry_options=retry_config
            ),
            description="A helpful AI assistant that can answer questions and perform web searches.",
            instruction=(
                "You are a helpful assistant. "
                "Provide clear, concise, and accurate responses. "
                "Use Google Search for current information or when you're unsure. "
                "Always format your responses in a readable way."
            ),
            tools=[google_search],
        )
        print("✅ Agent setup completed")
        return agent
    except ImportError as e:
        print(f"❌ Error importing required modules: {e}")
        print("Please make sure you have installed the required packages:")
        print("pip install google-adk python-dotenv")
        raise

async def run_queries(agent: Any) -> None:
    """Run example queries using the provided agent."""
    from google.adk.runners import InMemoryRunner
    
    print("\n" + "="*80)
    print("STARTING QUERIES".center(80))
    print("="*80)
    
    queries = [
        "What is Agent Development Kit from Google? What languages is the SDK available in?",
        "What's the current weather in London?"
        
    ]
    
    runner = InMemoryRunner(agent=agent)
    
    for i, query in enumerate(queries, 1):
        try:
            print(f"\n{' QUERY ' + str(i) + ' ':=^80}")
            print(f"🤔 {query}")
            
            # Run the query
            response = await runner.run_debug(query)
            
            # Format and print the response
            response_str = str(response)
            print("\n💡 Response:")
            print("-" * 80)
            print(textwrap.fill(response_str, width=80))
            print("-" * 80)
            
            # Save to PDF
            pdf_path = save_to_pdf(query, response_str)
            print(f"\n📄 Response saved to: {os.path.abspath(pdf_path)}")
            
        except Exception as e:
            print(f"\n❌ Error processing query: {e}")
            continue

def main():
    try:
        # Load environment and setup
        load_environment()
        agent = setup_agent()
        
        # Run the async queries
        asyncio.run(run_queries(agent))
        
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        return 1
    
    print("\n" + "="*80)
    print("SCRIPT COMPLETED SUCCESSFULLY".center(80))
    print("="*80)
    return 0

if __name__ == "__main__":
    exit(main())

import os
import asyncio
import json
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set up API key
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    print("🔑 Error: GOOGLE_API_KEY not found in .env file")
    exit(1)

os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY
print("✅ Environment variables loaded from .env file")

from google.adk.agents import Agent, SequentialAgent
from google.adk.models.google_llm import Gemini
from google.adk.runners import InMemoryRunner
from google.adk.tools import AgentTool, google_search
from google.genai import types

print("✅ ADK components imported successfully.")

retry_config = types.HttpRetryOptions(
    attempts=5,  # Maximum retry attempts
    exp_base=7,  # Delay multiplier
    initial_delay=1,
    http_status_codes=[429, 500, 503, 504],  # Retry on these HTTP errors
)

async def create_agents():
    # Research Agent
    research_agent = Agent(
        name="ResearchAgent",
        model=Gemini(
            model="gemini-2.5-flash-lite",
            retry_options=retry_config
        ),
        instruction="""You are a specialized research agent. Your only job is to use the
        google_search tool to find 2-3 pieces of relevant information on the given topic and present the findings with citations.""",
        tools=[google_search],
        output_key="research_findings",
    )
    print("✅ research_agent created.")

    # Summarizer Agent
    summarizer_agent = Agent(
        name="SummarizerAgent",
        model=Gemini(
            model="gemini-2.5-flash-lite",
            retry_options=retry_config
        ),
        instruction="""Read the provided research findings: {research_findings}
    Create a concise summary as a bulleted list with 3-5 key points.""",
        output_key="final_summary",
    )
    print("✅ summarizer_agent created.")

    # Root Coordinator
    root_agent = Agent(
        name="ResearchCoordinator",
        model=Gemini(
            model="gemini-2.5-flash-lite",
            retry_options=retry_config
        ),
        instruction="""You are a research coordinator. Your goal is to answer the user's query by orchestrating a workflow.
    1. First, you MUST call the `ResearchAgent` tool to find relevant information on the topic provided by the user.
    2. Next, after receiving the research findings, you MUST call the `SummarizerAgent` tool to create a concise summary.
    3. Finally, present the final summary clearly to the user as your response.""",
        tools=[AgentTool(research_agent), AgentTool(summarizer_agent)],
    )
    print("✅ root_agent created.")

    # Blog Pipeline Agents
    outline_agent = Agent(
        name="OutlineAgent",
        model=Gemini(
            model="gemini-2.5-flash-lite",
            retry_options=retry_config
        ),
        instruction="""Create a blog outline for the given topic with:
        1. A catchy headline
        2. An introduction hook
        3. 3-5 main sections with 2-3 bullet points for each
        4. A concluding thought""",
        output_key="blog_outline",
    )
    print("✅ outline_agent created.")

    writer_agent = Agent(
        name="WriterAgent",
        model=Gemini(
            model="gemini-2.5-flash-lite",
            retry_options=retry_config
        ),
        instruction="""Following this outline strictly: {blog_outline}
        Write a brief, 200 to 300-word blog post with an engaging and informative tone.""",
        output_key="blog_draft",
    )
    print("✅ writer_agent created.")

    editor_agent = Agent(
        name="EditorAgent",
        model=Gemini(
            model="gemini-2.5-flash-lite",
            retry_options=retry_config
        ),
        instruction="""Edit this draft: {blog_draft}
        Your task is to polish the text by fixing any grammatical errors, improving the flow and sentence structure, and enhancing overall clarity.""",
        output_key="final_blog",
    )
    print("✅ editor_agent created.")

    blog_pipeline = SequentialAgent(
        name="BlogPipeline",
        sub_agents=[outline_agent, writer_agent, editor_agent],
    )
    print("✅ Blog pipeline created.")

    return root_agent, blog_pipeline

async def main():
    try:
        # Create all agents
        research_agent, blog_pipeline = await create_agents()
        
        # Run research example
        print("\n=== Running Research Example ===")
        research_runner = InMemoryRunner(agent=research_agent)
        research_response = await research_runner.run_debug(
            "What are the latest advancements in quantum computing and what do they mean for AI?"
        )
        print("\nResearch Results:", research_response)
        
        # Run blog post example
        print("\n=== Running Blog Post Example ===")
        blog_runner = InMemoryRunner(agent=blog_pipeline)
        blog_response = await blog_runner.run_debug(
            "Write a blog post about the benefits of multi-agent systems for software developers"
        )
        print("\nBlog Post Results:", blog_response)

    except Exception as e:
        print(f"An error occurred: {str(e)}")

def ensure_dir(directory):
    """Create directory if it doesn't exist"""
    Path(directory).mkdir(parents=True, exist_ok=True)
    return directory

def extract_text_from_response(response):
    """Extract text from various response formats including Event objects"""
    if response is None:
        return "No response received"
        
    # If it's a string, return as is
    if isinstance(response, str):
        return response
        
    # If it has a text attribute, use that
    if hasattr(response, 'text'):
        return str(response.text)
        
    # If it's a list, join all text parts
    if isinstance(response, list):
        return ' '.join(str(item) for item in response)
        
    # If it's a dictionary, try to extract text from known keys
    if isinstance(response, dict):
        for key in ['text', 'content', 'response', 'result']:
            if key in response:
                return extract_text_from_response(response[key])
        # If no known keys, return string representation
        return str(response)
        
    # For any other type, try to get its string representation
    return str(response)

async def save_agent_output(output_dir: str, output_type: str, data: dict):
    """Save agent output to a JSON file"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(ensure_dir(os.path.join("agent_outputs", output_type)))
    output_file = output_dir / f"{output_type}_{timestamp}.txt"
    
    try:
        # Extract and format the content
        content = []
        for key, value in data.items():
            if key == 'response' or key == 'content':
                # Process the main content separately
                content.append(f"{key.upper()}:")
                content.append("-" * 40)
                content.append(extract_text_from_response(value))
                content.append("\n")
            else:
                # Process other fields
                content.append(f"{key.upper()}: {extract_text_from_response(value)}\n")
        
        # Write to file as plain text
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(content))
        
        print(f"\n📄 {output_type.capitalize()} output saved to: {output_file}")
        return str(output_file)
        
    except Exception as e:
        error_file = output_dir / f"{output_type}_error_{timestamp}.txt"
        with open(error_file, 'w', encoding='utf-8') as f:
            f.write(f"Error saving {output_type} output: {str(e)}\n")
            f.write(f"Original data type: {type(data)}\n")
            f.write("\nRaw data dump:\n")
            f.write(str(data))
        print(f"⚠️  Error saving {output_type} output, saved error details to: {error_file}")
        return str(error_file)

async def main():
    try:
        # Create agents
        research_agent, blog_pipeline = await create_agents()
        
        # Run research example
        print("\n=== Running Research Example ===")
        research_runner = InMemoryRunner(agent=research_agent)
        research_response = await research_runner.run_debug(
            "What are the latest advancements in quantum computing and what do they mean for AI?"
        )
        
# Save research output
        await save_agent_output("research", "research_results", {
            "query": "What are the latest advancements in quantum computing and what do they mean for AI?",
            "response": research_response,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "agent": "research_agent"
        })
        
        # Run blog post example
        print("\n=== Running Blog Post Example ===")
        blog_runner = InMemoryRunner(agent=blog_pipeline)
        blog_topic = "the benefits of multi-agent systems for software developers"
        blog_response = await blog_runner.run_debug(
            f"Write a blog post about {blog_topic}"
        )
        
# Save blog output
        await save_agent_output("blog", "blog_post", {
            "topic": blog_topic,
            "content": blog_response,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "agent": "blog_pipeline"
        })

    except Exception as e:
        print(f"An error occurred: {str(e)}")

def save_to_pdf(output_dir: str, filename: str, content: str, title: str = "Agent Output"):
    """Save content to a PDF file with proper formatting"""
    try:
        # Create output directory if it doesn't exist
        output_path = Path(ensure_dir(output_dir))
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_file = output_path / f"{filename}.pdf"
        
        # Create PDF
        pdf = FPDF()
        pdf.add_page()
        
        # Add title
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, title, 0, 1, 'C')
        pdf.ln(10)
        
        # Add content
        pdf.set_font("Arial", size=12)
        
        # Split content into lines and add to PDF
        for line in content.split('\n'):
            # Handle long lines by wrapping text
            if len(line) > 100:
                # Split long lines into multiple lines
                for i in range(0, len(line), 100):
                    pdf.cell(0, 10, line[i:i+100].strip(), 0, 1)
            else:
                pdf.cell(0, 10, line, 0, 1)
        
        # Save the PDF
        pdf.output(str(pdf_file))
        return str(pdf_file)
        
    except Exception as e:
        error_file = output_path / f"error_{timestamp}.txt"
        with open(error_file, 'w', encoding='utf-8') as f:
            f.write(f"Error creating PDF: {str(e)}\n")
            f.write("Content that caused the error:\n")
            f.write(content[:1000])  # Save first 1000 chars of content for debugging
        return str(error_file)

# Update your save_agent_output function to use save_to_pdf
async def save_agent_output(output_dir: str, output_type: str, data: dict):
    """Save agent output to a PDF file"""
    try:
        # Prepare content
        content = []
        for key, value in data.items():
            if key in ['response', 'content']:
                content.append(f"{key.upper()}:\n{'-'*40}\n{extract_text_from_response(value)}\n")
            else:
                content.append(f"{key.upper()}: {extract_text_from_response(value)}\n")
        
        content_str = '\n'.join(content)
        
        # Save to PDF
        from fpdf import FPDF  # Import here to ensure it's available
        pdf_path = save_to_pdf(
            os.path.join("agent_outputs", output_dir),
            output_type,
            content_str,
            title=f"{output_type.replace('_', ' ').title()}"
        )
        
        print(f"\n📄 PDF saved to: {pdf_path}")
        return pdf_path
        
    except Exception as e:
        print(f"⚠️ Error saving {output_type} output: {str(e)}")
        error_file = f"agent_outputs/error_{output_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(error_file, 'w', encoding='utf-8') as f:
            f.write(f"Error details: {str(e)}\n")
        return error_file
def ensure_dir(directory):
    """Create directory if it doesn't exist"""
    import os
    os.makedirs(directory, exist_ok=True)
    return directory

def save_blog_output(output_dir: str, outline: str, content: str, editor_content: str):
    """Save the blog post to a nicely formatted PDF"""
    try:
        # Create PDF
        from fpdf import FPDF
        
        pdf = FPDF()
        pdf.add_page()
        
        # Set font and styles
        pdf.set_font("Arial", size=12)
        
        # Add title
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, "Multi-Agent Systems for Developers", ln=True, align='C')
        pdf.ln(10)
        
        # Add outline section
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, "Outline:", ln=True)
        pdf.set_font("Arial", size=12)
        pdf.multi_cell(0, 10, outline)
        pdf.ln(10)
        
        # Add content section
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, "Blog Content:", ln=True)
        pdf.set_font("Arial", size=12)
        pdf.multi_cell(0, 10, content)
        pdf.ln(10)
        
        # Add editor's version
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, "Editor's Version:", ln=True)
        pdf.set_font("Arial", size=12)
        pdf.multi_cell(0, 10, editor_content)
        
        # Save the PDF
        output_file = f"{output_dir}/multi_agent_blog.pdf"
        pdf.output(output_file)
        print(f"📄 Blog post saved to: {output_file}")
        return output_file
        
    except Exception as e:
        print(f"⚠️ Error saving blog post: {str(e)}")
        return None 
        
def format_blog_post(outline, content, editor_content):
    """Format the blog post with proper sections and styling"""
    formatted = f"""### Created new session: debug_session_id

User > Write a blog post about the benefits of multi-agent systems for software developers

{outline}

{content}

{editor_content}
"""
    return formatted

async def save_blog_output(output_dir: str, outline: str, content: str, editor_content: str):
    """Save the blog post to a nicely formatted PDF"""
    try:
        # Create PDF
        from fpdf import FPDF
        
        pdf = FPDF()
        pdf.add_page()
        
        # Set font and styles
        pdf.set_font("Arial", size=12)
        
        # Add title
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, "Multi-Agent Systems for Developers", ln=True, align='C')
        pdf.ln(10)
        
        # Add outline section
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, "Outline:", ln=True)
        pdf.set_font("Arial", size=12)
        pdf.multi_cell(0, 10, outline)
        pdf.ln(10)
        
        # Add content section
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, "Blog Content:", ln=True)
        pdf.set_font("Arial", size=12)
        pdf.multi_cell(0, 10, content)
        pdf.ln(10)
        
        # Add editor's version
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, "Editor's Version:", ln=True)
        pdf.set_font("Arial", size=12)
        pdf.multi_cell(0, 10, editor_content)
        
        # Save the PDF
        output_file = f"{output_dir}/multi_agent_blog.pdf"
        pdf.output(output_file)
        print(f"📄 Blog post saved to: {output_file}")
        return output_file
        
    except Exception as e:
        print(f"⚠️ Error saving blog post: {str(e)}")
        return None

from fpdf import FPDF
from pathlib import Path
import os
from datetime import datetime
def save_research_to_pdf(output_dir: str, research_data: dict):
    """Save research output to a well-formatted PDF file"""
    try:
        # Create PDF
        pdf = FPDF()
        pdf.add_page()
        
        # Set font and styles
        pdf.set_font("Arial", size=12)
        
        # Add title
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, "Research Findings", ln=True, align='C')
        pdf.ln(10)
        
        # Add metadata
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, "Query:", ln=True)
        pdf.set_font("Arial", size=12)
        pdf.multi_cell(0, 10, research_data.get('query', 'No query provided'))
        pdf.ln(5)
        
        # Add timestamp
        pdf.set_font("Arial", 'I', 10)
        pdf.cell(0, 10, f"Generated on: {research_data.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}")
        pdf.ln(10)
        
        # Add main content
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, "Research Results:", ln=True)
        pdf.ln(5)
        
        # Process and add the research content
        pdf.set_font("Arial", size=12)
        content = extract_text_from_response(research_data.get('response', 'No response content'))
        
        # Split into paragraphs and add to PDF
        paragraphs = content.split('\n\n')
        for para in paragraphs:
            if para.strip():  # Skip empty paragraphs
                pdf.multi_cell(0, 10, para)
                pdf.ln(5)
        
        # Save the PDF
        output_dir = Path(ensure_dir(output_dir))
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"research_findings_{timestamp}.pdf"
        pdf.output(str(output_file))
        
        print(f"📄 Research findings saved to: {output_file}")
        return str(output_file)
        
    except Exception as e:
        print(f"⚠️ Error saving research PDF: {str(e)}")
        return None
async def save_agent_output(output_dir: str, output_type: str, data: dict):
    """Save agent output to a file (PDF for research, text for others)"""
    try:
        if output_type == "research_results":
            # Use PDF for research results
            return save_research_to_pdf(os.path.join("agent_outputs", output_dir), data)
        else:
            # Use existing text-based saving for other types
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = Path(ensure_dir(os.path.join("agent_outputs", output_type)))
            output_file = output_dir / f"{output_type}_{timestamp}.txt"
            
            content = []
            for key, value in data.items():
                if key == 'response' or key == 'content':
                    content.append(f"{key.upper()}:\n{'-'*40}\n{extract_text_from_response(value)}\n")
                else:
                    content.append(f"{key.upper()}: {extract_text_from_response(value)}\n")
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(content))
            
            print(f"\n📄 {output_type.capitalize()} output saved to: {output_file}")
            return str(output_file)
            
    except Exception as e:
        error_file = Path("agent_outputs") / f"error_{output_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(error_file, 'w', encoding='utf-8') as f:
            f.write(f"Error saving {output_type} output: {str(e)}\n")
        print(f"⚠️ Error saving {output_type} output, saved error details to: {error_file}")
        return str(error_file)



if __name__ == "__main__":
    # Create main output directory
    ensure_dir("agent_outputs")
    asyncio.run(main())




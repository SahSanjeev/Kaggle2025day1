import os
import asyncio
from dotenv import load_dotenv
from google.adk.agents import Agent, ParallelAgent, SequentialAgent
from google.adk.models.google_llm import Gemini
from google.adk.runners import InMemoryRunner
from google.adk.tools import google_search
from google.genai import types

# Load environment variables from .env file
load_dotenv()
from fpdf import FPDF
from pathlib import Path
from datetime import datetime

# Set up API key
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    print("🔑 Error: GOOGLE_API_KEY not found in .env file")
    exit(1)

os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY
print("✅ Environment variables loaded from .env file")

# Configure retry settings
retry_config = types.HttpRetryOptions(
    attempts=5,
    exp_base=2,
    initial_delay=1,
    http_status_codes=[429, 500, 503, 504],
)

# Tech Researcher: Focuses on AI and ML trends.
tech_researcher = Agent(
    name="TechResearcher",
    model=Gemini(
        model="gemini-2.5-flash-lite",
        retry_options=retry_config
    ),
    instruction="""Research the latest AI/ML trends. Include 3 key developments,
the main companies involved, and the potential impact. Keep the report very concise (100 words).""",
    tools=[google_search],
    output_key="tech_research",
)

print("✅ tech_researcher created.")

# Health Researcher: Focuses on medical breakthroughs.
health_researcher = Agent(
    name="HealthResearcher",
    model=Gemini(
        model="gemini-2.5-flash-lite",
        retry_options=retry_config
    ),
    instruction="""Research recent medical breakthroughs. Include 3 significant advances,
their practical applications, and estimated timelines. Keep the report concise (100 words).""",
    tools=[google_search],
    output_key="health_research",
)

print("✅ health_researcher created.")

# Finance Researcher: Focuses on fintech trends.
finance_researcher = Agent(
    name="FinanceResearcher",
    model=Gemini(
        model="gemini-2.5-flash-lite",
        retry_options=retry_config
    ),
    instruction="""Research current fintech trends. Include 3 key trends,
their market implications, and the future outlook. Keep the report concise (100 words).""",
    tools=[google_search],
    output_key="finance_research",
)

print("✅ finance_researcher created.")

# The AggregatorAgent runs *after* the parallel step to synthesize the results.
aggregator_agent = Agent(
    name="AggregatorAgent",
    model=Gemini(
        model="gemini-2.5-flash-lite",
        retry_options=retry_config
    ),
    instruction="""Combine these three research findings into a single executive summary:

**Technology Trends:**
{tech_research}

**Health Breakthroughs:**
{health_research}

**Finance Innovations:**
{finance_research}

Your summary should highlight common themes, surprising connections, and the most important key takeaways from all three reports. The final summary should be around 200 words.""",
    output_key="executive_summary",
)

print("✅ aggregator_agent created.")

# The ParallelAgent runs all its sub-agents simultaneously.
parallel_research_team = ParallelAgent(
    name="ParallelResearchTeam",
    sub_agents=[tech_researcher, health_researcher, finance_researcher],
)

# This SequentialAgent defines the high-level workflow
root_agent = SequentialAgent(
    name="ResearchSystem",
    sub_agents=[parallel_research_team, aggregator_agent],
)

print("✅ Parallel and Sequential Agents created.")

async def main():
    try:
        runner = InMemoryRunner(agent=root_agent)
        print("\n🚀 Starting parallel research...")
        response = await runner.run_debug(
            "Run the daily executive briefing on Tech, Health, and Finance"
        )
        
        # Print the final executive summary
        print("\n" + "="*80)
        print("EXECUTIVE SUMMARY")
        print("="*80)
        print(response)
        
        # Save to PDF
        pdf_path = save_executive_summary_pdf(response)
        if pdf_path:
            print(f"\n✅ Report saved to: {pdf_path}")
        
        return response
        
    except Exception as e:
        print(f"\n❌ An error occurred: {str(e)}")
        return None

from fpdf import FPDF
from pathlib import Path
from datetime import datetime

def save_executive_summary_pdf(summary):
    """Save the executive summary to a PDF file in the reports directory"""
    try:
        # Convert summary to string if it's a list
        if isinstance(summary, list):
            # If it's a list of content parts, join them with newlines
            if all(hasattr(item, 'text') for item in summary):
                summary = '\n\n'.join(part.text for part in summary if hasattr(part, 'text'))
            else:
                summary = '\n\n'.join(str(item) for item in summary)
        
        # Create reports directory if it doesn't exist
        reports_dir = Path("reports")
        reports_dir.mkdir(exist_ok=True)
        
        # Create PDF
        pdf = FPDF()
        pdf.add_page()
        
        # Add title
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, "Executive Summary", ln=True, align='C')
        pdf.ln(10)
        
        # Add date
        pdf.set_font("Arial", 'I', 10)
        pdf.cell(0, 10, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True)
        pdf.ln(10)
        
        # Add content
        pdf.set_font("Arial", size=12)
        
        # Split the summary into lines and process each line
        for line in str(summary).split('\n'):
            line = line.strip()
            if not line:
                pdf.ln(5)  # Add extra space for empty lines
                continue
                
            # Check if line is a section header (starts with **)
            if line.startswith('**') and line.endswith('**'):
                pdf.set_font("Arial", 'B', 14)
                pdf.cell(0, 10, line.strip('*').strip(), ln=True)
                pdf.set_font("Arial", size=12)
            else:
                pdf.multi_cell(0, 10, line)
            pdf.ln(2)  # Small space between lines
        
        # Save the PDF
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = reports_dir / f"executive_summary_{timestamp}.pdf"
        pdf.output(str(output_file))
        
        print(f"\n📄 Executive summary saved to: {output_file}")
        return str(output_file)
        
    except Exception as e:
        print(f"\n⚠️ Error saving PDF: {str(e)}")
        import traceback
        traceback.print_exc()  # Print full traceback for debugging
        return None






if __name__ == "__main__":
    asyncio.run(main())
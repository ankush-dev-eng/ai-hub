import os
import sys
import urllib.parse
from pathlib import Path
from dotenv import load_dotenv
from PIL import Image
from mcp.server.mcpserver import MCPServer
import httpx

# Load environment variables from .env next to this script with override
dotenv_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path, override=True)

server = MCPServer("hackathon-ai-hub")

@server.tool()
def groq_fast_query(prompt: str, model: str = "openai/gpt-oss-120b") -> str:
    """Run an ultra-fast LLM query via Groq Cloud (300+ tokens/sec).
    Available models: 'openai/gpt-oss-120b', 'qwen/qwen3.8-27b', 'openai/gpt-oss-20b'.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return "Error: GROQ_API_KEY not found in environment or .env"
    from groq import Groq
    client = Groq(api_key=api_key)
    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Groq Error: {e}"

@server.tool()
def gemini_vision_analyze(image_paths: str, instruction: str = "Analyze these images in detail. Identify key elements, flaws, data, and recommendations.") -> str:
    """Analyze one or more local images or screenshots using Google Gemini 3.8 Flash multimodal vision.
    image_paths: Comma-separated list of image paths or a single image path.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "Error: GEMINI_API_KEY not found in environment or .env"
    
    paths = [p.strip() for p in image_paths.split(",") if p.strip()]
    images = []
    for p in paths:
        path = Path(p).expanduser().resolve()
        if not path.is_file():
            return f"Error: Image file not found at {path}"
        try:
            images.append(Image.open(path))
        except Exception as e:
            return f"Error opening image {path}: {e}"
            
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        contents = images + [instruction]
        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=contents
        )
        return response.text
    except Exception as e:
        # Fallback to gemini-3.5-flash if 3.8 is busy
        try:
            response = client.models.generate_content(
                model="gemini-3.5-flash",
                contents=contents
            )
            return response.text
        except Exception as e2:
            return f"Gemini Vision Error: {e} (Fallback also failed: {e2})"

@server.tool()
def gemini_deep_reasoning(prompt: str) -> str:
    """Query Google Gemini 3.8 Flash for deep analytical reasoning, document breakdown, or complex questions."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "Error: GEMINI_API_KEY not found in environment or .env"
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=prompt
        )
        return response.text
    except Exception as e:
        return f"Gemini Error: {e}"

@server.tool()
def free_cloud_image_generate(prompt: str, output_path: str = "generated_image.png", model: str = "flux") -> str:
    """Generate an image in the cloud using FLUX.1 (100% free, 0% laptop GPU, no credit card).
    Saves the image directly to output_path.
    """
    try:
        encoded_prompt = urllib.parse.quote(prompt)
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&model={model}&nologo=true"
        with httpx.Client(timeout=60.0, follow_redirects=True) as client:
            resp = client.get(url)
            resp.raise_for_status()
            out_p = Path(output_path).resolve()
            with open(out_p, "wb") as f:
                f.write(resp.content)
            return f"Image successfully generated and saved to {out_p}"
    except Exception as e:
        return f"Cloud Image Generation Error: {e}"

if __name__ == "__main__":
    server.run(transport="stdio")

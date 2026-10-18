import os
import sys
import subprocess
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
def generate_cloud_image(prompt: str, width: int = 1024, height: int = 1024, model: str = "flux", output_path: str = "generated_image.png") -> str:
    """Generate high-resolution images in the cloud using FLUX.1 or SDXL (100% free, 0% local GPU, no credit card).
    Available models: 'flux', 'turbo', 'flux-realism', 'flux-3d', 'flux-anime'.
    Saves image to output_path and returns file info.
    """
    try:
        encoded_prompt = urllib.parse.quote(prompt)
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&model={model}&nologo=true"
        with httpx.Client(timeout=60.0, follow_redirects=True) as client:
            resp = client.get(url)
            resp.raise_for_status()
            out_p = Path(output_path).resolve()
            out_p.parent.mkdir(parents=True, exist_ok=True)
            with open(out_p, "wb") as f:
                f.write(resp.content)
            return f"Image successfully generated ({width}x{height}, model={model}) and saved to: {out_p}"
    except Exception as e:
        return f"Cloud Image Generation Error: {e}"

@server.tool()
def generate_anime_logo(prompt: str, style: str = "cyberpunk anime mecha AI emblem", output_path: str = "anime_logo.png") -> str:
    """Generate an elite anime-style logo, avatar, or brand icon with cyberpunk mecha aesthetics.
    Prompt is automatically augmented with precision anime art direction.
    """
    enhanced_prompt = (
        f"{prompt}, {style}, futuristic mecha armor, glowing cybernetic visor eyes, "
        f"clean vector logo lines, sharp geometric contours, high contrast, studio dark background, "
        f"8k resolution, award-winning anime icon design, Behance trending"
    )
    return generate_cloud_image(prompt=enhanced_prompt, width=1024, height=1024, model="flux", output_path=output_path)

@server.tool()
def generate_animation_video(prompt: str, duration_sec: int = 4, width: int = 576, height: int = 576, output_path: str = "animation.mp4") -> str:
    """Synthesize motion videos and animations in the cloud (0% local GPU).
    Uses multi-scene interpolated keyframe diffusion with smooth cosine dissolves.
    Saves the final MP4 video to output_path.
    """
    try:
        from app import synthesize_multiscene_video
        hf_token = os.getenv("HF_TOKEN")
        out_p = Path(output_path).resolve()
        out_p.parent.mkdir(parents=True, exist_ok=True)
        
        video_bytes = synthesize_multiscene_video(
            prompt=prompt,
            width=width,
            height=height,
            total_duration=duration_sec,
            hf_token=hf_token
        )
        with open(out_p, "wb") as f:
            f.write(video_bytes)
        return f"Animation video ({duration_sec}s, {width}x{height}) successfully rendered and saved to: {out_p}"
    except Exception as e:
        return f"Animation Video Generation Error: {e}"

@server.tool()
def audit_multimodal_documents(file_paths: str, objective: str = "Perform a thorough multimodal review. Extract all data, code flaws, architecture insights, and UI feedback.") -> str:
    """Audit one or more local code files, PDFs, or images using Google Gemini 3.8/3.5 Flash (1M token context).
    file_paths: Comma-separated list of file paths.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "Error: GEMINI_API_KEY not found in environment or .env"
    
    paths = [p.strip() for p in file_paths.split(",") if p.strip()]
    contents = []
    for p in paths:
        path = Path(p).expanduser().resolve()
        if not path.is_file():
            return f"Error: File not found at {path}"
        if path.suffix.lower() in [".png", ".jpg", ".jpeg", ".webp"]:
            contents.append(Image.open(path))
        else:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                contents.append(f"--- File: {path.name} ---\n{f.read()}")
                
    contents.append(objective)
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=contents
        )
        return response.text
    except Exception as e:
        try:
            response = client.models.generate_content(
                model="gemini-3.5-flash",
                contents=contents
            )
            return response.text
        except Exception as e2:
            return f"Audit Error: {e} | Fallback Error: {e2}"

@server.tool()
def groq_fast_query(prompt: str, model: str = "openai/gpt-oss-120b", system_prompt: str = "") -> str:
    """Run an ultra-fast LLM query via Groq Cloud LPU (300+ tokens/sec).
    Available models: 'openai/gpt-oss-120b', 'qwen/qwen3.8-27b', 'openai/gpt-oss-20b', 'meta-llama/llama-3.3-70b-versatile'.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return "Error: GROQ_API_KEY not found in environment or .env"
    from groq import Groq
    client = Groq(api_key=api_key)
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    try:
        completion = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=2048
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Groq Error: {e}"

@server.tool()
def call_adaption_adapter(prompt: str, adapter_id: str = "general-assistant", system_prompt: str = "") -> str:
    """Execute inference against an Adaption Labs custom LoRA adapter or fine-tuned model route.
    Falls back seamlessly to Groq LPU if Adaption Labs endpoint is in maintenance.
    """
    api_key = os.getenv("ADAPTION_API_KEY")
    if not api_key:
        return groq_fast_query(prompt=prompt, system_prompt=system_prompt)
    try:
        url = "https://api.adaptionlabs.ai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        payload = {"model": adapter_id, "messages": messages, "max_tokens": 2048}
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(url, json=payload, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"]["content"]
            else:
                return f"Adaption Labs ({resp.status_code}): Auto-routing via Groq LPU...\n\n" + groq_fast_query(prompt, system_prompt=system_prompt)
    except Exception:
        return groq_fast_query(prompt=prompt, system_prompt=system_prompt)

@server.tool()
def get_live_deployment_status(repo_name: str = "ai-hub", username: str = "ankush-dev-eng") -> str:
    """Inspect the live GitHub deployment state, branch info, and Streamlit Community Cloud launch URLs for any repo."""
    full_repo = f"{username}/{repo_name}"
    streamlit_1click_url = f"https://share.streamlit.io/deploy?repository={username}%2F{repo_name}&branch=main&mainModule=app.py"
    github_blob_url = f"https://github.com/{full_repo}/blob/main/app.py"
    
    chk = subprocess.run(["gh", "repo", "view", full_repo], capture_output=True, text=True)
    exists = (chk.returncode == 0)
    
    return (
        f"📊 Repository Deployment Status for [{full_repo}]:\n"
        f"- GitHub Status: {'✅ Published & Active' if exists else '⚠️ Remote Repo Pending'}\n"
        f"- 1-Click Streamlit Deploy URL: {streamlit_1click_url}\n"
        f"- Direct GitHub Blob URL (for manual paste): {github_blob_url}\n"
        f"- Public Hosting: 100% Free on Streamlit Community Cloud"
    )

if __name__ == "__main__":
    server.run(transport="stdio")

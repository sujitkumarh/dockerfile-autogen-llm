import subprocess
import os
import sys
import re
from pathlib import Path

def get_project_structure(project_path):
    if sys.platform == "win32":
        # Fallback for Windows: use os.walk
        result = []
        level_limit = 2
        base_path = Path(project_path).resolve()

        for root, dirs, files in os.walk(base_path):
            depth = len(Path(root).relative_to(base_path).parts)
            if depth > level_limit:
                del dirs[:]  # Don't recurse further
                continue

            indent = "  " * depth
            result.append(f"{indent}{Path(root).name}/")
            for f in files:
                result.append(f"{indent}  {f}")
        return "\n".join(result)
    else:
        # Linux/Mac/WSL
        return subprocess.check_output(['tree', '-L', '2', project_path]).decode()

def generate_dockerfile(prompt, model="llama3.2"):
    result = subprocess.run(
        ["ollama", "run", model],
        input=prompt.encode(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    stdout = result.stdout.decode()
    stderr = result.stderr.decode()

    if stderr:
        print("⚠️ STDERR from Ollama:\n", stderr)

    if not stdout.strip():
        print("❌ LLM returned no output.")
    else:
        print("✅ LLM Output:\n", stdout[:500], "\n...")

    return stdout

def clean_dockerfile(text):
    """Strip markdown, code fences, explanations from LLM output."""
    lines = text.strip().splitlines()
    dockerfile_lines = []
    for line in lines:
        if line.strip().startswith("```") or "explain" in line.lower():
            continue
        if line.strip().startswith("#") and "use" in line.lower():
            continue
        dockerfile_lines.append(line)
    return "\n".join(dockerfile_lines)

def validate_copy_paths(dockerfile, project_dir):
    """Warn if COPY paths refer to non-existent files."""
    missing_files = []
    copy_lines = re.findall(r'^COPY\s+(.+?)\s', dockerfile, flags=re.MULTILINE)
    for item in copy_lines:
        # Support single or multiple source COPY
        sources = item.strip().split()
        for src in sources:
            source_path = Path(project_dir) / src
            if not source_path.exists():
                missing_files.append(str(source_path))
    return missing_files

if __name__ == "__main__":
    project_dir = "sample-app"
    description = "This is a DevOps project using Ansible to install Nginx. It contains a playbook and requirements.txt for Python modules."

    try:
        structure = get_project_structure(project_dir)
    except Exception as e:
        print("❌ Failed to get project structure:", e)
        exit(1)

    template_path = Path("prompt_template.txt")
    if not template_path.exists():
        print("❌ prompt_template.txt is missing.")
        exit(1)

    template = template_path.read_text()
    prompt = template.format(
        project_description=description,
        file_structure=structure
    )

    dockerfile_raw = generate_dockerfile(prompt)
    dockerfile_clean = clean_dockerfile(dockerfile_raw)

    if dockerfile_clean.strip():
        # Validate COPY paths
        missing = validate_copy_paths(dockerfile_clean, project_dir)
        if missing:
            print("⚠️ Warning: Some COPY source paths do not exist:")
            for m in missing:
                print("   -", m)

        with open("Dockerfile", "w") as f:
            f.write(dockerfile_clean)

        print("✅ Dockerfile cleaned, validated, and saved.")
    else:
        print("❌ Dockerfile was empty. Not saved.")


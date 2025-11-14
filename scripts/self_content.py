import argparse
import json
import os
from datetime import datetime

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


# -------------------------
# Helpers
# -------------------------

def load_topics(path):
    """Load list of content topics from config/content_topics.json."""
    if not os.path.exists(path):
        return ["Industrial AI", "Autonomous Manufacturing", "Multi-Agent Systems"]

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("topics", [])
    except Exception:
        return ["Industrial AI", "Autonomous Manufacturing", "Multi-Agent Systems"]


def generate_markdown_post(topic, model="gpt-4.1-mini"):
    """Generate a markdown blog post using OpenAI."""
    if OpenAI is None:
        return f"# Draft Post\n\n## {topic}\n\n(Placeholder — OpenAI client missing)"

    client = OpenAI()
    prompt = f"""
    Write a concise, high-quality blog article about:
    **{topic}**
    Focus on Industrial AI, Multi-Agent Systems, automotive value chains, and autonomy.
    """

    response = client.responses.create(
        model=model,
        input=prompt
    )

    content = response.output_text
    return f"# {topic}\n\n{content}"


def write_output(md, out_dir):
    """Write generated markdown file."""
    os.makedirs(out_dir, exist_ok=True)
    filename = datetime.utcnow().strftime("%Y%m%d_%H%M_content.md")
    out_path = os.path.join(out_dir, filename)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(md)

    return out_path


# -------------------------
# Main CLI logic
# -------------------------

def main():
    parser = argparse.ArgumentParser(description="Self Content Agent")

    parser.add_argument(
        "-t", "--topic",
        required=True,
        help="Content topic the agent should write about"
    )

    parser.add_argument(
        "--root",
        default=".",
        help="Repository root"
    )

    parser.add_argument(
        "--out",
        default="ops/content",
        help="Output directory for draft content"
    )

    args = parser.parse_args()

    # Load topics if topic = "auto"
    if args.topic == "auto":
        topic_list = load_topics(os.path.join(args.root, "config", "content_topics.json"))
        topic = topic_list[0] if topic_list else "Industrial AI"
    else:
        topic = args.topic

    # Generate markdown
    md = generate_markdown_post(topic)

    # Write to file
    out_file = write_output(
        md,
        os.path.join(args.root, args.out)
    )

    print(f"Generated content draft: {out_file}")


if __name__ == "__main__":
    main()

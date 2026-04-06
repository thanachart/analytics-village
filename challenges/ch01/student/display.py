"""
Analytics Village — Display helpers for Colab-friendly output.
"""
from __future__ import annotations


def format_table(headers: list[str], rows: list[list], title: str = None) -> str:
    """Format a table for display."""
    try:
        from tabulate import tabulate
        result = ""
        if title:
            result += f"\n{'=' * 60}\n{title}\n{'=' * 60}\n"
        result += tabulate(rows, headers=headers, tablefmt="simple")
        return result
    except ImportError:
        lines = []
        if title:
            lines.append(f"\n{'=' * 60}")
            lines.append(title)
            lines.append("=" * 60)
        lines.append(" | ".join(str(h) for h in headers))
        lines.append("-" * (sum(len(str(h)) for h in headers) + 3 * len(headers)))
        for row in rows:
            lines.append(" | ".join(str(c) for c in row))
        return "\n".join(lines)


def format_qa_answer(question_id: str, question: str, answer: str, owner_name: str) -> str:
    """Format a Q&A answer for display."""
    width = 60
    return (
        f"\n{'=' * width}\n"
        f"Q [{question_id}]: {question}\n"
        f"{'=' * width}\n"
        f"{owner_name}: \"{answer}\"\n"
        f"{'=' * width}\n"
    )


def format_brief(text: str) -> str:
    """Display brief text, attempting markdown rendering in Colab."""
    try:
        from IPython.display import display, Markdown
        display(Markdown(text))
        return ""
    except ImportError:
        return text


def format_validation(results: list[tuple[bool, str]]) -> str:
    """Format validation results."""
    lines = ["\n" + "=" * 40]
    all_valid = True
    for ok, msg in results:
        icon = "+" if ok else "X"
        lines.append(f"  [{icon}] {msg}")
        if not ok:
            all_valid = False
    lines.append("=" * 40)
    if all_valid:
        lines.append("VALID - Ready to submit. Run d.export() to save.")
    else:
        lines.append("NOT VALID - Fix the above before submitting.")
    return "\n".join(lines)

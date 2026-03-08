"""BIP inline review flow for terminal-based draft approval.

PLAN-313: a/e/s keystroke approval between work.
- a = approve (queue to Typefully)
- e = edit (open in editor)
- s = skip (defer for later)
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class ReviewResult:
    action: str  # "approved", "edited", "skipped", "no_drafts"
    draft_id: str | None = None
    message: str = ""


def get_pending_drafts(bip_dir: str) -> list[dict]:
    """Get drafts pending review."""
    drafts_dir = os.path.join(bip_dir, "drafts")
    if not os.path.isdir(drafts_dir):
        return []

    drafts = []
    for fname in sorted(os.listdir(drafts_dir)):
        if fname.endswith(".json"):
            path = os.path.join(drafts_dir, fname)
            try:
                with open(path) as f:
                    draft = json.load(f)
                draft["_path"] = path
                draft["_id"] = fname.replace(".json", "")
                drafts.append(draft)
            except (json.JSONDecodeError, OSError):
                continue
    return drafts


def display_draft(draft: dict) -> None:
    """Display a draft for review."""
    print("\n" + "=" * 60)
    print(f"Draft: {draft.get('_id', 'unknown')}")
    print(f"Source: {draft.get('source', 'unknown')}")
    print(f"Created: {draft.get('created_at', 'unknown')}")
    print("-" * 60)
    print(draft.get("content", draft.get("draft", "(no content)")))
    print("=" * 60)


def approve_draft(draft: dict, bip_dir: str) -> bool:
    """Approve draft and queue to Typefully."""
    try:
        from scripts.lib.crux_typefully import TypefullyClient, queue_draft

        client = TypefullyClient(bip_dir=bip_dir)
        content = draft.get("content", draft.get("draft", ""))

        result = queue_draft(client, content)

        if result.get("success"):
            # Move draft to approved/
            approved_dir = os.path.join(bip_dir, "approved")
            os.makedirs(approved_dir, exist_ok=True)

            draft_path = draft.get("_path")
            if draft_path and os.path.exists(draft_path):
                approved_path = os.path.join(approved_dir, os.path.basename(draft_path))
                os.rename(draft_path, approved_path)

            return True
    except Exception as e:
        print(f"Error approving: {e}")
    return False


def edit_draft(draft: dict) -> str | None:
    """Open draft in editor, return edited content."""
    editor = os.environ.get("EDITOR", "vim")
    content = draft.get("content", draft.get("draft", ""))

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(content)
        temp_path = f.name

    try:
        subprocess.run([editor, temp_path], check=True)
        with open(temp_path) as f:
            edited = f.read()
        return edited
    except subprocess.CalledProcessError:
        return None
    finally:
        try:
            os.unlink(temp_path)
        except OSError:
            pass


def skip_draft(draft: dict, bip_dir: str) -> None:
    """Mark draft as skipped (defer for later)."""
    skipped_dir = os.path.join(bip_dir, "skipped")
    os.makedirs(skipped_dir, exist_ok=True)

    draft_path = draft.get("_path")
    if draft_path and os.path.exists(draft_path):
        skipped_path = os.path.join(skipped_dir, os.path.basename(draft_path))
        os.rename(draft_path, skipped_path)


def review_single(draft: dict, bip_dir: str) -> ReviewResult:
    """Review a single draft with a/e/s prompt."""
    display_draft(draft)

    print("\n[a]pprove  [e]dit  [s]kip  [q]uit")

    while True:
        try:
            choice = input("> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return ReviewResult(action="quit")

        if choice == "a":
            if approve_draft(draft, bip_dir):
                return ReviewResult(
                    action="approved",
                    draft_id=draft.get("_id"),
                    message="Queued to Typefully"
                )
            else:
                return ReviewResult(
                    action="error",
                    draft_id=draft.get("_id"),
                    message="Failed to approve"
                )

        elif choice == "e":
            edited = edit_draft(draft)
            if edited and edited != draft.get("content", draft.get("draft", "")):
                # Update draft file
                draft_path = draft.get("_path")
                if draft_path:
                    draft["content"] = edited
                    draft["edited_at"] = datetime.now(timezone.utc).isoformat()
                    with open(draft_path, "w") as f:
                        json.dump(draft, f, indent=2)
                return ReviewResult(
                    action="edited",
                    draft_id=draft.get("_id"),
                    message="Draft updated"
                )
            else:
                print("No changes made")
                continue

        elif choice == "s":
            skip_draft(draft, bip_dir)
            return ReviewResult(
                action="skipped",
                draft_id=draft.get("_id"),
                message="Deferred for later"
            )

        elif choice == "q":
            return ReviewResult(action="quit")

        else:
            print("Invalid choice. Use a/e/s/q")


def review_all(bip_dir: str) -> list[ReviewResult]:
    """Review all pending drafts."""
    drafts = get_pending_drafts(bip_dir)

    if not drafts:
        print("No drafts pending review.")
        return [ReviewResult(action="no_drafts")]

    print(f"\n{len(drafts)} draft(s) pending review.\n")

    results = []
    for draft in drafts:
        result = review_single(draft, bip_dir)
        results.append(result)

        if result.action == "quit":
            break

        print(f"\n{result.action}: {result.message}")

    return results


def main() -> None:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Review BIP drafts")
    parser.add_argument("--bip-dir", default=".crux/bip", help="BIP directory")
    args = parser.parse_args()

    bip_dir = args.bip_dir
    if not os.path.isabs(bip_dir):
        bip_dir = os.path.join(os.getcwd(), bip_dir)

    if not os.path.isdir(bip_dir):
        print(f"BIP directory not found: {bip_dir}")
        sys.exit(1)

    results = review_all(bip_dir)

    # Summary
    approved = sum(1 for r in results if r.action == "approved")
    edited = sum(1 for r in results if r.action == "edited")
    skipped = sum(1 for r in results if r.action == "skipped")

    if approved + edited + skipped > 0:
        print(f"\nSummary: {approved} approved, {edited} edited, {skipped} skipped")


if __name__ == "__main__":
    main()

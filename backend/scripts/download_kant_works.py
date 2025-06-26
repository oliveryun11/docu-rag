#!/usr/bin/env python3
"""
Script to download Immanuel Kant's major philosophical works from Project Gutenberg
and organize them in the docs_data directory for the RAG system.
"""

import os
import requests
import time
from pathlib import Path
from urllib.parse import urljoin
import re

# Project Gutenberg URLs for Kant's major works
KANT_WORKS = {
    "critique_of_pure_reason": {
        "title": "Critique of Pure Reason",
        "url": "https://www.gutenberg.org/files/4280/4280-0.txt",
        "filename": "01-critique-of-pure-reason.txt"
    },
    "critique_of_practical_reason": {
        "title": "Critique of Practical Reason", 
        "url": "https://www.gutenberg.org/files/5683/5683-0.txt",
        "filename": "02-critique-of-practical-reason.txt"
    },
    "critique_of_judgment": {
        "title": "Critique of Judgment",
        "url": "https://www.gutenberg.org/files/48433/48433-0.txt", 
        "filename": "03-critique-of-judgment.txt"
    },
    "groundwork_metaphysics_morals": {
        "title": "Fundamental Principles of the Metaphysics of Morals",
        "url": "https://www.gutenberg.org/files/5682/5682-0.txt",
        "filename": "04-groundwork-metaphysics-of-morals.txt"
    },
    "prolegomena": {
        "title": "Prolegomena to Any Future Metaphysics",
        "url": "https://www.gutenberg.org/files/35629/35629-0.txt",
        "filename": "05-prolegomena-to-any-future-metaphysics.txt"
    },
    "religion_within_bounds": {
        "title": "Religion Within the Bounds of Bare Reason",
        "url": "https://www.gutenberg.org/files/38148/38148-0.txt",
        "filename": "06-religion-within-bounds-of-bare-reason.txt"
    },
    "what_is_enlightenment": {
        "title": "What is Enlightenment?",
        "url": "https://www.gutenberg.org/files/45988/45988-0.txt",
        "filename": "07-what-is-enlightenment.txt"
    },
    "perpetual_peace": {
        "title": "Perpetual Peace",
        "url": "https://www.gutenberg.org/files/50922/50922-0.txt",
        "filename": "08-perpetual-peace.txt"
    }
}

def clean_gutenberg_text(text):
    """
    Clean Project Gutenberg text by removing header/footer and formatting.
    """
    # Find the start of the actual content (after the Gutenberg header)
    start_markers = [
        "*** START OF THE PROJECT GUTENBERG",
        "*** START OF THIS PROJECT GUTENBERG", 
        "*END*THE SMALL PRINT!"
    ]
    
    end_markers = [
        "*** END OF THE PROJECT GUTENBERG",
        "*** END OF THIS PROJECT GUTENBERG",
        "End of the Project Gutenberg"
    ]
    
    # Find start position
    start_pos = 0
    for marker in start_markers:
        pos = text.find(marker)
        if pos != -1:
            # Find the end of this line
            start_pos = text.find('\n', pos) + 1
            break
    
    # Find end position
    end_pos = len(text)
    for marker in end_markers:
        pos = text.find(marker)
        if pos != -1:
            end_pos = pos
            break
    
    # Extract the main content
    content = text[start_pos:end_pos].strip()
    
    # Clean up excessive whitespace
    content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
    content = re.sub(r' +', ' ', content)
    
    return content

def download_work(work_key, work_info, output_dir):
    """
    Download a single work from Project Gutenberg.
    """
    print(f"Downloading: {work_info['title']}")
    
    try:
        response = requests.get(work_info['url'], timeout=30)
        response.raise_for_status()
        
        # Clean the text
        clean_content = clean_gutenberg_text(response.text)
        
        # Add metadata header
        header = f"""---
title: {work_info['title']}
author: Immanuel Kant
source: Project Gutenberg
url: {work_info['url']}
downloaded: {time.strftime('%Y-%m-%d')}
---

"""
        
        final_content = header + clean_content
        
        # Save to file
        file_path = output_dir / work_info['filename']
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(final_content)
        
        print(f"✓ Saved: {work_info['filename']}")
        return True
        
    except requests.RequestException as e:
        print(f"✗ Failed to download {work_info['title']}: {e}")
        return False
    except Exception as e:
        print(f"✗ Error processing {work_info['title']}: {e}")
        return False

def main():
    """
    Main function to download all Kant works.
    """
    # Set up output directory
    script_dir = Path(__file__).parent
    backend_dir = script_dir.parent
    docs_data_dir = backend_dir / "docs_data"
    kant_dir = docs_data_dir / "kant"
    
    # Create directories if they don't exist
    kant_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Downloading Kant's works to: {kant_dir}")
    print("=" * 50)
    
    successful_downloads = 0
    total_works = len(KANT_WORKS)
    
    for work_key, work_info in KANT_WORKS.items():
        if download_work(work_key, work_info, kant_dir):
            successful_downloads += 1
        
        # Be respectful to Project Gutenberg servers
        time.sleep(1)
    
    print("=" * 50)
    print(f"Download complete: {successful_downloads}/{total_works} works downloaded successfully")
    
    if successful_downloads > 0:
        print(f"\nFiles saved to: {kant_dir}")
        print("\nTo index these documents in your RAG system, run:")
        print("python scripts/bulk_index_docs.py")

if __name__ == "__main__":
    main() 
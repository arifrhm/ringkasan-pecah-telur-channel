#!/usr/bin/env python3
"""
parse_transcript.py: Membersihkan raw VTT file dan mengelompokkan teks ber-timestamp.
"""

import re
from pathlib import Path

def parse_vtt(vtt_path):
    with open(vtt_path, 'r', encoding='utf-8') as f:
        content = f.read()

    cues = re.split(r'\n\s*\n', content)
    raw_segments = []
    last_text = ''

    for cue in cues:
        cue = cue.strip()
        if not cue or cue.startswith('WEBVTT') or '-->' not in cue:
            continue
        
        lines = cue.split('\n')
        time_match = re.search(r'(\d+:\d+:\d+\.\d+|\d+:\d+\.\d+)\s*-->\s*(\d+:\d+:\d+\.\d+|\d+:\d+\.\d+)', lines[0])
        if not time_match:
            continue
            
        start_raw = time_match.group(1)
        parts = start_raw.split(':')
        if len(parts) == 3:
            s_val = int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        else:
            s_val = int(parts[0]) * 60 + float(parts[1])
        s_int = int(s_val)

        raw_text = ' '.join(lines[1:])
        clean = re.sub(r'<[^>]+>', '', raw_text)
        clean = re.sub(r'align:[^\s]+|position:[^\s]+', '', clean)
        clean = re.sub(r'\s+', ' ', clean).strip()

        if not clean or clean == last_text:
            continue
        
        if last_text and clean.startswith(last_text):
            clean = clean[len(last_text):].strip()
        if not clean:
            continue

        last_text = clean
        raw_segments.append({'seconds': s_int, 'text': clean})

    # Group into time blocks (~25-40 seconds interval) to provide coherent context
    grouped_blocks = []
    if not raw_segments:
        return grouped_blocks

    current_start = raw_segments[0]['seconds']
    current_texts = []

    for seg in raw_segments:
        if (seg['seconds'] - current_start) >= 30 and current_texts:
            full_block_text = ' '.join(current_texts)
            mm = current_start // 60
            ss = current_start % 60
            grouped_blocks.append({
                'seconds': current_start,
                'time_str': f"{mm:02d}:{ss:02d}",
                'text': full_block_text
            })
            current_start = seg['seconds']
            current_texts = [seg['text']]
        else:
            current_texts.append(seg['text'])

    if current_texts:
        mm = current_start // 60
        ss = current_start % 60
        grouped_blocks.append({
            'seconds': current_start,
            'time_str': f"{mm:02d}:{ss:02d}",
            'text': ' '.join(current_texts)
        })

    return grouped_blocks

def format_transcript_for_prompt(grouped_blocks):
    lines = []
    for b in grouped_blocks:
        lines.append(f"[{b['time_str']}] (detik {b['seconds']}): {b['text']}")
    return "\n".join(lines)

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        blocks = parse_vtt(sys.argv[1])
        print(f"Total blocks: {len(blocks)}")
        for b in blocks[:5]:
            print(f"[{b['time_str']}] ({b['seconds']}s): {b['text'][:80]}...")

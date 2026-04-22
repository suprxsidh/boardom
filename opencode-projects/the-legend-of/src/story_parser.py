#!/usr/bin/env python3
"""
Story Parser - Converts story markdown to engine-ready JSON
Parses scenes, choices, and metadata from velanthor-story.md
"""

import re
import json


def parse_story_file(input_file, output_file):
    """Parse story markdown into JSON scenes."""
    
    with open(input_file, 'r') as f:
        content = f.read()
    
    scenes = {}
    current_char = None
    current_scene_id = None
    current_scene_data = None
    in_description = False
    
    lines = content.split('\n')
    
    for line in lines:
        line = line.rstrip()
        
        # Detect character sections
        char_match = re.match(r'^## (KIRA|THERON|VEX|ELARA)[A-Z_]+:', line)
        if char_match:
            current_char = char_match.group(1)
            continue
        
        # Skip scene divider lines
        if line.startswith('---'):
            continue
        
        # Detect scene headers like **SCENE: SCENE_ID**
        scene_match = re.match(r'\*\*SCENE: ([A-Z0-9_]+)\*\*', line)
        if scene_match:
            # Save previous scene
            if current_scene_data and current_scene_id:
                scenes[current_scene_id] = current_scene_data
            
            current_scene_id = scene_match.group(1)
            current_scene_data = {
                'id': current_scene_id,
                'character': current_char,
                'description': '',
                'choices': [],
                'type': 'story'
            }
            in_description = True
            continue
        
        # Look for {Type: X} metadata
        type_match = re.match(r'\{Type: ([a-z]+)\}', line)
        if type_match and current_scene_data:
            current_scene_data['type'] = type_match.group(1)
        
        # Detect ending tags
        if '{ENDING:' in line and current_scene_data:
            ending_match = re.search(r'\{ENDING: ([A-Za-z_]+)\}', line)
            if ending_match:
                current_scene_data['ending'] = ending_match.group(1)
        
        # Detect choice sections
        if '[CHOICE:' in line:
            in_description = False
            continue
        
        # Parse choice options - handle various formats
        # Format: - A: **Text** — description {metadata}
        # Also: - A: **Text** — description
        choice_match = re.match(r'- ([ABCD]): \*\*([^*]+)\*\* (.+)', line)
        if choice_match and current_scene_data:
            letter = choice_match.group(1)
            text = choice_match.group(2).strip()
            full_text = choice_match.group(3).strip()
            
            # Parse metadata from full_text
            choice_data = {
                'letter': letter,
                'text': text,
                'full_text': full_text,
                'leads_to': None,
                'effects': {},
                'requires': None
            }
            
            # Extract LEADS TO
            leads_match = re.search(r'LEADS TO: ([A-Z0-9_]+)', full_text)
            if leads_match:
                choice_data['leads_to'] = leads_match.group(1)
            
            # Extract REQUIRES
            req_match = re.search(r'REQUIRES: ([^}]+)', full_text)
            if req_match:
                choice_data['requires'] = req_match.group(1).strip()
            
            # Extract EFFECTs
            eff_match = re.search(r'EFFECT: ([^}]+)', full_text)
            if eff_match:
                eff_text = eff_match.group(1)
                effects = {}
                for part in eff_text.split(','):
                    part = part.strip()
                    if part.startswith('+') and len(part) > 1:
                        try:
                            stat = part[2:].strip().lower().replace(' ', '_')
                            effects[stat] = int(part[1])
                        except:
                            pass
                    elif part.startswith('-') and len(part) > 1:
                        try:
                            stat = part[2:].strip().lower().replace(' ', '_')
                            effects[stat] = int(part[1])
                        except:
                            pass
                choice_data['effects'] = effects
            
            current_scene_data['choices'].append(choice_data)
        
        # Collect description text
        elif in_description and current_scene_data and line.strip():
            if not line.startswith('**') and not line.startswith('[CHOICE'):
                current_scene_data['description'] += line + '\n'
    
    # Save last scene
    if current_scene_data and current_scene_id:
        scenes[current_scene_id] = current_scene_data
    
    # Save to JSON
    with open(output_file, 'w') as f:
        json.dump(scenes, f, indent=2)
    
    return len(scenes)


def main():
    input_file = '../docs/story/velanthor-story.md'
    output_file = '../data/story.json'
    
    count = parse_story_file(input_file, output_file)
    print(f"Parsed {count} scenes to {output_file}")


if __name__ == '__main__':
    main()
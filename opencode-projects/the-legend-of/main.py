#!/usr/bin/env python3
"""
Velanthor RPG - Main Entry Point
A dark fantasy choice-based terminal RPG.
"""

import sys
import os
import json

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.engine import GameEngine, CYAN, YELLOW, GREEN, RED, RESET, BOLD
from scripts.intro import display_intro, get_characters, show_character_selection


def load_story_scenes():
    """Load story scenes from JSON."""
    try:
        with open('data/story.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"{RED}Story data not found. Run story_parser.py first.{RESET}")
        return {}


def create_character(choice, engine):
    """Set up player based on character choice."""
    
    characters = {
        'A': {
            'name': 'Kira Nightwind',
            'tagline': 'The void calls to you. Will you answer?',
            'class': 'Void Mage',
            'stats': {
                'strength': 4, 'dexterity': 6, 'intelligence': 8,
                'charisma': 5, 'void_magic': 7, 'combat': 3,
                'stealth': 4, 'influence': 2
            },
            'inventory': ['void spellbook', 'mother\'s locket'],
            'start_scene': 'KIRA_CH1_THORNWICK'
        },
        'B': {
            'name': 'Theron Ashford',
            'tagline': 'You were the greatest knight. Then you ran.',
            'class': 'Knight',
            'stats': {
                'strength': 8, 'dexterity': 6, 'intelligence': 5,
                'charisma': 6, 'void_magic': 0, 'combat': 9,
                'stealth': 3, 'influence': 4
            },
            'inventory': ['rusty sword', 'old shield'],
            'start_scene': 'THERON_CH1_TAVERN'
        },
        'C': {
            'name': 'Vex Shadowstep',
            'tagline': 'Trust is a commodity. You are the product.',
            'class': 'Shadow',
            'stats': {
                'strength': 5, 'dexterity': 9, 'intelligence': 7,
                'charisma': 6, 'void_magic': 0, 'combat': 4,
                'stealth': 10, 'influence': 5
            },
            'inventory': ['lockpicking tools', 'crown piece'],
            'start_scene': 'VEX_CH1_DOCKS'
        },
        'D': {
            'name': 'Elara Vance',
            'tagline': 'Your parents are dead. The truth awaits.',
            'class': 'Merchant',
            'stats': {
                'strength': 4, 'dexterity': 5, 'intelligence': 9,
                'charisma': 8, 'void_magic': 0, 'combat': 2,
                'stealth': 4, 'influence': 8
            },
            'inventory': ['trading ledger', 'letter of credit'],
            'start_scene': 'ELARA_CH1_ESTATE'
        }
    }
    
    if choice not in characters:
        return None
    
    char = characters[choice]
    engine.player = char['name']
    engine.stats = char['stats'].copy()
    engine.inventory = char['inventory'].copy()
    engine.current_scene = char['start_scene']
    
    return engine


def display_scene(scene_data, engine):
    """Display a scene and handle choices."""
    print(f"\n{BOLD}{CYAN}{'─' * 60}{RESET}")
    
    # Show scene description
    description = scene_data.get('description', '').strip()
    if description:
        print(description)
    
    # Check for ending
    if 'ending' in scene_data:
        ending = scene_data['ending']
        print(f"\n{BOLD}{GREEN}═══ ENDING: {ending} ═══{RESET}")
        return 'ending'
    
    # Show choices - hide all technical tags from user
    choices = scene_data.get('choices', [])
    if choices:
        print(f"\n{BOLD}What do you do?{RESET}")
        for choice in choices:
            letter = choice['letter']
            text = choice['text']
            # Hide all technical tags - just show letter and text
            print(f"  {YELLOW}[{letter}]{RESET} {text}")
    else:
        # No choices - auto-advance immediately without prompting
        return 'auto'
    
    return 'continue'


def handle_choice(scene_data, choice_letter, engine, scenes):
    """Process player choice and navigate to next scene."""
    choices = scene_data.get('choices', [])
    
    # Find choice - exact match OR first available
    chosen_choice = None
    for choice in choices:
        if choice['letter'].upper() == choice_letter.upper():
            chosen_choice = choice
            break
    
    # If no exact match, use first available choice
    if not chosen_choice and choices:
        chosen_choice = choices[0]
        print(f"{YELLOW}Using {chosen_choice['letter']} instead.{RESET}")
    
    if chosen_choice:
        # Check requirements
        req = chosen_choice.get('requires')
        if req:
            meets_req, fail_msg = engine.check_requirements(req)
            if not meets_req:
                print(f"{RED}Cannot: {fail_msg}{RESET}")
                return engine.current_scene
        
        # Apply effects
        effects = chosen_choice.get('effects', {})
        for stat, value in effects.items():
            if stat in engine.stats:
                engine.stats[stat] += value
        
        # Navigate to next scene
        next_scene = chosen_choice.get('leads_to')
        if next_scene and next_scene in scenes:
            return next_scene
        elif next_scene:
            return None
    
    print(f"{YELLOW}Invalid choice.{RESET}")
    return scene_data.get('id', engine.current_scene)


def show_tutorial():
    """Show the tutorial."""
    print(f"""
{BOLD}{CYAN}╔══════════════════════════════════════════════════════════════╗
║                      TUTORIAL                              ║
╚══════════════════════════════════════════════════════════════╝{RESET}

{YELLOW}MAKING CHOICES:{RESET}
  - Each scene presents choices labeled [A], [B], [C], [D]
  - Type the letter and press ENTER to choose
  - Some choices require certain stats (shown in {YELLOW}yellow{RESET})

{YELLOW}STATS:{RESET}
  - STR (Strength): Physical power, combat damage
  - DEX (Dexterity): Agility, stealth, dodging
  - INT (Intelligence): Knowledge, puzzle solving
  - CHA (Charisma): Persuasion, leadership
  - Class skills: Void Magic, Combat, Stealth, Influence

{YELLOW}COMBAT:{RESET}
  - [A] Attack: Roll STR + Combat vs enemy defense
  - [B] Defend: Reduce incoming damage
  - [C] Use Skill: Class-specific abilities
  - [D] Flee: Attempt to escape

{YELLOW}TIPS:{RESET}
  - Type {CYAN}stats{RESET} anytime to view your stats
  - Type {CYAN}inventory{RESET} to check your items
  - Type {CYAN}save{RESET} to save your progress
  - Type {CYAN}quit{RESET} to exit

{GREEN}Good luck, traveler. The fate of Velanthor rests with you.{RESET}
""")
    input("\nPress ENTER to begin...")


def main():
    """Main game loop."""
    # Load story data
    scenes = load_story_scenes()
    if not scenes:
        return
    
    engine = GameEngine()
    
    # Show intro
    display_intro()
    
    # Check for saved game and handle continuation
    import os
    save_exists = os.path.exists('savegame.json')
    should_continue = False
    
    if save_exists:
        print(f"\n{YELLOW}You have a saved game.{RESET}")
        print(f"  {YELLOW}[C]{RESET} Continue")
        print(f"  {YELLOW}[N]{RESET} New game")
        
        save_choice = input("\nChoice: ").strip().upper()
        
        if save_choice == 'C':
            engine = GameEngine()
            if engine.load_game('savegame.json'):
                should_continue = True
                print(f"{GREEN}Continuing your adventure as {engine.player}...{RESET}")
            else:
                print(f"{YELLOW}Save corrupted. Starting new game.{RESET}")
        elif save_choice == 'N':
            pass  # New game
        else:
            pass  # Default to new game
    
    if not should_continue:
        # Character selection
        characters = get_characters()
        choice = show_character_selection(characters)
        
        if choice not in characters:
            print(f"{RED}Invalid choice. Exiting.{RESET}")
            return
        
        # Create character
        create_character(choice, engine)
        
        print(f"\n{GREEN}You are now {engine.player}, a {characters[choice]['class']}.{RESET}")
        
        # Show tutorial only on new game
        show_tutorial()
    
    # Main game loop - story navigation
    while True:
        scene_id = engine.current_scene
        
        if not scene_id:
            print(f"\n{BOLD}{CYAN}THE END{RESET}")
            break
        
        if scene_id not in scenes:
            print(f"\n{RED}Scene not found: {scene_id}{RESET}")
            break
        
        scene_data = scenes[scene_id]
        
        # Display scene
        result = display_scene(scene_data, engine)
        
        if result == 'ending':
            break
        
        # Auto-advance through scenes without choices - immediate, no prompt
        if result == 'auto':
            char_prefix = scene_id.split('_')[0]
            # Sort scenes properly
            all_scenes = sorted([s for s in scenes.keys() if s.startswith(char_prefix)],
                               key=lambda x: int(x.split('_CH')[1].split('_')[0]) if '_CH' in x else 0)
            
            current_idx = all_scenes.index(scene_id) if scene_id in all_scenes else 0
            
            # Find next scene with choices AFTER current
            next_scene = None
            for i in range(current_idx + 1, len(all_scenes)):
                sid = all_scenes[i]
                if len(scenes[sid].get('choices', [])) > 0:
                    next_scene = sid
                    break
            
            # If no next with choices, try ANY next scene (will auto-advance again)
            if not next_scene and current_idx + 1 < len(all_scenes):
                next_scene = all_scenes[current_idx + 1]
            
            if next_scene:
                engine.current_scene = next_scene
                continue
            else:
                print(f"\n{RED}End of story path.{RESET}")
                break
        
        # Get player choice
        choice_input = input(f"\n{RESET}> ").strip().upper()
        
        # Handle empty input
        if choice_input == '':
            continue
        
        if choice_input in ['QUIT', 'EXIT']:
            print(f"{YELLOW}Are you sure you want to quit? (y/n){RESET}")
            if input("> ").strip().lower() == 'y':
                break
        elif choice_input == 'STATS':
            engine.show_stats()
            continue
        elif choice_input == 'INVENTORY':
            engine.show_inventory()
            continue
        elif choice_input == 'HELP':
            show_tutorial()
            continue
        elif choice_input == 'SAVE':
            engine.save_game('savegame.json')
            continue
        elif choice_input == 'LOAD':
            if engine.load_game('savegame.json'):
                print(f"{GREEN}Game loaded.{RESET}")
            continue
        
        # Handle story choice
        next_scene = handle_choice(scene_data, choice_input, engine, scenes)
        
        # If leads_to scene doesn't exist OR leads_to is None, find next with choices
        if not next_scene or next_scene not in scenes:
            char_prefix = scene_id.split('_')[0]
            # Get all scenes for this character, sorted by chapter
            all_scenes = sorted([s for s in scenes.keys() if s.startswith(char_prefix)], 
                              key=lambda x: int(x.split('_CH')[1].split('_')[0]) if '_CH' in x else 0)
            
            current_idx = all_scenes.index(scene_id) if scene_id in all_scenes else 0
            
            # Find next scene AFTER current with choices
            next_scene = None
            for i in range(current_idx + 1, len(all_scenes)):
                sid = all_scenes[i]
                if len(scenes[sid].get('choices', [])) > 0:
                    next_scene = sid
                    break
            
            # If no next with choices, look for ANY next scene (will auto-advance)
            if not next_scene and current_idx + 1 < len(all_scenes):
                next_scene = all_scenes[current_idx + 1]
        
        engine.current_scene = next_scene
    
    print(f"\n{CYAN}Thanks for playing Velanthor!{RESET}")


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""Intro screen for Velanthor RPG."""

import sys
import os

VELANTHOR_ART = r"""
    _______                   _              ______                _             
   / _____)                 | |            (____ \              | |            
  ( (____  _____  ___  ____ | |  _  ____    _____) )  ___  ____ | |  _  ____   
   \____ \| ___ |/___)/ _  )| | / )/ _  )  |  ____/  / _ \|  _ \| | / )/ _  )  
   _____) ) ____|___ ( (/ / | |( (( (/ /   | |      | |_| | | | | |( (( (/ /   
  (______/|_____|___/ \____)|_/  \____)   |_|       \___/|_| |_||_| \____)   
                                                                               
   _____                   _              _______                 _             
  / ____)                 | |            (_______)               | |            
 ( (____  _____  ___  ____| |  _  ____    _______  _   _  ____  | |  _  ____  
  \____ \| ___ |/___)/ _  | | / )/ _  )  |  ___  || | | ||  _ \ | | / )/ _ )  
  _____) ) ____|___ ( (/ /| |( (( (/ /   | |   | || |_| || | | || |( (( (/ /  
 (______/|_____|___/ \____)|_/  \____)   |_|   |_||____/ |_| |_||_| \____)  
"""


PREMISE = """
The world of Velanthor remembers the old ways.

Two thousand years ago, the Void Kingdom fell in a single night—the Sundering.
Aethon the Undying, king of the void, shattered into seven pieces.
Crown fragments scattered across the land, each carrying power beyond mortal comprehension.

Now, the Five Kingdoms tear at each other's throats.
The Cult of the Hollow seeks to reunite the crown and unleash the Void Beast.
The Silent Church claims it will bring peace.
And the Ashen Wastes grow larger each year.

You are a wanderer in a dying world. A knight who lost honor. A mage who hides her nature.
A thief carrying impossible cargo. A merchant seeking vengeance.

The choice is yours.

What legend will you carve into the history of Velanthor?
"""


def clear_screen():
    """Clear the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')


def display_intro():
    """Display the main intro screen."""
    clear_screen()
    print(VELANTHOR_ART)
    print("\n" + "=" * 60)
    print("          VELANTHOR: THE CROWN OF THE DEAD GOD")
    print("=" * 60 + "\n")
    print(PREMISE)
    print("\n" + "=" * 60)
    input("\n              [ Press any key to begin ]")
    print("=" * 60)


def show_character_selection(characters):
    """Show character selection menu."""
    clear_screen()
    print("\n" + "=" * 60)
    print("              CHOOSE YOUR DESTINY")
    print("=" * 60 + "\n")
    
    for key, char in characters.items():
        print(f"  [{key}] {char['name']}")
        print(f"      {char['tagline']}")
        print(f"      Class: {char['class']}")
        print(f"      Start: {char['start']}\n")
    
    print("=" * 60)
    choice = input("  Select your character: ").strip().upper()
    return choice


def get_characters():
    """Return available characters."""
    return {
        'A': {
            'name': 'Kira Nightwind',
            'tagline': 'The void calls to you. Will you answer?',
            'class': 'Void Mage',
            'start': 'Thornwick'
        },
        'B': {
            'name': 'Theron Ashford',
            'tagline': 'You were the greatest knight. Then you ran.',
            'class': 'Knight',
            'start': 'Dustwall'
        },
        'C': {
            'name': 'Vex Shadowstep',
            'tagline': 'Trust is a commodity. You are the product.',
            'class': 'Shadow',
            'start': 'Theris Docks'
        },
        'D': {
            'name': 'Elara Vance',
            'tagline': 'Your parents are dead. The truth awaits.',
            'class': 'Merchant',
            'start': 'Theris'
        }
    }


def main():
    """Main intro flow."""
    display_intro()
    
    characters = get_characters()
    choice = show_character_selection(characters)
    
    if choice in characters:
        char = characters[choice]
        print(f"\nYou have chosen: {char['name']}")
        input("\n[ Press any key to begin your journey ]")
        return char
    
    return None


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""Narrator class for Velanthor RPG - handles flavor text and scene transitions."""


class Narrator:
    """Narrator for descriptive text, atmosphere, and transitions."""
    
    def __init__(self):
        self.current_location = None
        self.time_of_day = "dawn"
    
    def describe(self, text):
        """Display descriptive narration text."""
        print(f"\n[ {text} ]\n")
    
    def transition(self, from_location, to_location):
        """Display a transition between locations."""
        print(f"\n{'=' * 50}")
        print(f"  The journey continues...")
        print(f"  {from_location}  →  {to_location}")
        print(f"{'=' * 50}\n")
    
    def time_passes(self, days=1):
        """Indicate time passing."""
        print(f"\n  ... {days} day{'s' if days > 1 else ''} pass{'es' if days > 1 else 's'} ...\n")
    
    def atmosphere(self, mood):
        """Set the atmosphere/mood for a scene."""
        mood_texts = {
            "tense": "The air is thick with tension. Something is wrong.",
            "eerie": "A chill runs down your spine. This place feels... wrong.",
            "ominous": "Dark clouds gather above. The world holds its breath.",
            "peaceful": "For a moment, all is quiet. The world breathes.",
            "dangerous": "Your hand drifts to your weapon. Trust no one.",
            "mysterious": "Secrets hide in every shadow. The truth waits.",
            "melancholy": "A sadness lingers in the air. Remember the fallen.",
            "hopeful": "A spark of hope flickers. Change is coming.",
            "chaotic": "Panic fills the air. Everything is falling apart.",
            "cold": "The cold bites at your bones. Winter has teeth.",
        }
        if mood in mood_texts:
            self.describe(mood_texts[mood])
    
    def describe_location(self, name, description):
        """Describe a new location."""
        print(f"\n{'─' * 40}")
        print(f"  📍 {name}")
        print(f"{'─' * 40}")
        print(f"  {description}\n")
    
    def combat_start(self, enemy_name):
        """Announce combat start."""
        print(f"\n{'!' * 50}")
        print(f"  ⚔️  ENCOUNTER: {enemy_name}")
        print(f"{'!' * 50}\n")
    
    def combat_end(self, result="victory"):
        """Announce combat end."""
        results = {
            "victory": "The enemy falls. You survive... for now.",
            "defeat": "Darkness consumes you. Everything fades...",
            "escape": "You flee into the shadows. Live to fight another day.",
            "draw": "Neither side yields. The battle ends in stalemate.",
        }
        print(f"\n{'─' * 30}")
        print(f"  {results.get(result, result)}")
        print(f"{'─' * 30}\n")
    
    def reveal(self, text):
        """Reveal important information."""
        print(f"\n★  {text}  ★\n")
    
    def whisper(self, text):
        """Whispered text - subtle hints."""
        print(f"\n  ... {text} ...\n")
    
    def choice_prompt(self):
        """Prompt for player choice."""
        print(f"\n{'─' * 30}")
        print("  What will you do?")
        print(f"{'─' * 30}\n")
    
    def stat_check(self, stat, difficulty):
        """Announce a stat check."""
        print(f"\n[ Checking {stat} (DC: {difficulty}) ]")
    
    def stat_check_result(self, success):
        """Announce stat check result."""
        if success:
            print("  ✓ Success!\n")
        else:
            print("  ✗ Failure\n")
    
    def inventory_update(self, item, action="add"):
        """Announce inventory change."""
        action_text = "obtained" if action == "add" else "lost"
        print(f"\n  [ {action_text.upper()}: {item} ]\n")
    
    def quest_update(self, quest_name, status):
        """Announce quest update."""
        status_texts = {
            "start": "A new quest begins",
            "update": "Your objectives have changed",
            "complete": "Quest complete",
            "fail": "Quest failed",
        }
        print(f"\n  📜 {quest_name}")
        print(f"     {status_texts.get(status, status)}\n")
    
    def character_thought(self, text):
        """Show character inner thought."""
        print(f"\n  * {text} *\n")
    
    def npc_speaks(self, name, text):
        """Show NPC dialogue."""
        print(f'\n  "{name}": "{text}"\n')
    
    def weather(self, condition):
        """Set weather description."""
        weather_texts = {
            "rain": "Rain falls in sheets, soaking everything.",
            "storm": "Thunder rumbles. Lightning splits the sky.",
            "snow": "Snow blankets the world in white silence.",
            "fog": "Thick fog obscures everything around you.",
            "clear": "The sky is clear. Stars shine bright.",
            "wind": "A cold wind howls through the land.",
            "heat": "The heat is oppressive. Sweat drips.",
        }
        if condition in weather_texts:
            self.describe(weather_texts[condition])
    
    def time_of_day_update(self, time):
        """Update and display time of day."""
        self.time_of_day = time
        time_descriptions = {
            "dawn": "The sun rises. A new day begins.",
            "morning": "Morning light bathes the world.",
            "noon": "The sun reaches its zenith.",
            "afternoon": "Shadows lengthen as day fades.",
            "dusk": "Twilight paints the sky in orange and purple.",
            "night": "Darkness falls. Secrets emerge.",
            "midnight": "The witching hour. Nothing stirs.",
        }
        if time in time_descriptions:
            self.describe(time_descriptions[time])
    
    def faction_event(self, faction, event):
        """Display faction-related world events."""
        print(f"\n{'─' * 40}")
        print(f"  ⚑ {faction}: {event}")
        print(f"{'─' * 40}\n")
    
    def ending(self, ending_type, title):
        """Display ending."""
        endings = {
            "good": "★",
            "neutral": "◈",
            "bad": "✧",
            "dark": "◆",
        }
        symbol = endings.get(ending_type, "●")
        print(f"\n{'═' * 50}")
        print(f"  {symbol}  {title}  {symbol}")
        print(f"{'═' * 50}\n")
    
    def divider(self, char="-", length=40):
        """Display a divider line."""
        print(f"\n{char * length}\n")
    
    def pause(self):
        """Pause for dramatic effect."""
        input("\n  [ Press any key to continue ]")


def create_narrator():
    """Factory function to create a narrator instance."""
    return Narrator()


if __name__ == "__main__":
    narrator = create_narrator()
    narrator.describe("The narrator is ready.")
    narrator.transition("Thornwick", "Crownhaven")
    narrator.atmosphere("eerie")
    narrator.pause()
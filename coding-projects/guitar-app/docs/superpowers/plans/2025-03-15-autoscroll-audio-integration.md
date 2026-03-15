# Autoscroll & Audio Integration Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a Tab Player that provides audio-driven autoscroll with real-time feedback, stopping on mistakes, and a clean professional UI.

**Architecture:** Create a `TabPlayer` container component that manages state and coordinates `TabViewer`, `AutoscrollCtrl`, and `AudioFeedbackPanel`. Integrate existing `useAudioCapture` hook for pitch detection and implement note matching logic.

**Tech Stack:** React 18, TypeScript, Vite, Web Audio API, CSS (existing Tailwind/App.css), existing mock API

---

## File Structure Map

**New Files:**
- `src/components/TabPlayer.tsx` - Main container with state management
- `src/components/AutoscrollCtrl.tsx` - Playback controls and speed
- `src/components/TabPlayerSettings.tsx` - Settings panel (stop on mistake, tolerance)
- `src/components/AudioFeedbackPanel.tsx` - Recent notes display
- `src/utils/noteMatching.ts` - Note validation and matching algorithm
- `src/utils/scrollController.ts` - Smooth scrolling logic
- `src/hooks/useTabPlayer.ts` - Extracted player logic (optional for now, keep in component)

**Modified Files:**
- `src/App.tsx` - Replace current TabViewer/Autoscroll with TabPlayer wrapper
- `src/App.css` - Add new styles for TabPlayer components (or reuse existing)
- `src/components/TabViewer.tsx` - Accept position/highlights props, update rendering
- `src/components/Autoscroll.tsx` - Will be replaced by AutoscrollCtrl, can delete
- `src/hooks/useAudioCapture.ts` - Enhance to return better data, fix TODO

**Test Files:**
- `src/components/__tests__/TabPlayer.test.tsx`
- `src/components/__tests__/TabViewer.test.tsx`
- `src/utils/__tests__/noteMatching.test.ts`
- `src/utils/__tests__/scrollController.test.ts`

---

## Chunk 1: Core Types and Utilities (Foundation)

### Task 1: Define TypeScript Interfaces

**Files:**
- Create: `src/utils/types.ts` (or add to existing `src/types.ts`)
- Modify: None

**Steps:**

- [ ] **Step 1:** Add new interfaces to `src/types.ts` for player state, settings, and highlights

```typescript
// Add to src/types.ts after existing code

export interface PlayerStatus {
  type: 'stopped' | 'playing' | 'paused' | 'stopped-on-mistake';
}

export interface PlayerSettings {
  stopOnMistake: boolean;
  pitchTolerance: number; // cents, default 25
  scrollMode: 'auto' | 'manual';
  autoScrollSpeed: number; // BPM (60-180)
}

export interface DetectedNote {
  note: TabNote;
  pitch: number; // Hz
  timestamp: number;
  confidence: number;
  pitchDeviation?: number; // cents from expected
}

export interface HighlightedNote {
  lineIndex: number;
  noteIndex: number;
  status: 'correct' | 'incorrect' | 'current' | 'pending';
}

export interface PlayerMetrics {
  totalNotesPlayed: number;
  correctNotes: number;
  incorrectNotes: number;
  avgPitchDeviation: number;
  startTime: number | null;
  elapsedTime: number;
}
```

- [ ] **Step 2:** Run TypeScript compiler to check for errors

Run: `npx tsc --noEmit`
Expected: No errors

- [ ] **Step 3:** Commit type additions

```bash
git add src/types.ts
git commit -m "feat: add player state types and interfaces"
```

---

### Task 2: Implement Note Matching Utility

**Files:**
- Create: `src/utils/noteMatching.ts`
- Test: `src/utils/__tests__/noteMatching.test.ts`

**Steps:**

- [ ] **Step 1:** Write failing tests for `getNoteFrequency` and `findBestNoteMatch`

```typescript
// src/utils/__tests__/noteMatching.test.ts
import { getNoteFrequency, findBestNoteMatch } from '../noteMatching';
import { TabNote } from '../types';

describe('getNoteFrequency', () => {
  it('returns correct frequency for E2 open string', () => {
    const frequency = getNoteFrequency(6, 0); // 6th string, open
    expect(frequency).toBeCloseTo(82.41, 1); // E2 ≈ 82.41 Hz
  });

  it('returns correct frequency for A2 5th fret on 6th string', () => {
    const frequency = getNoteFrequency(6, 5);
    expect(frequency).toBeCloseTo(110.00, 1); // A2
  });
});

describe('findBestNoteMatch', () => {
  const detectedNote: TabNote = { string: 6, fret: 0, timestamp: 0 };

  it('matches exact note', () => {
    const expectedNotes: TabNote[] = [
      { string: 6, fret: 0, timestamp: 0 }
    ];
    const match = findBestNoteMatch(detectedNote, expectedNotes, 25);
    expect(match).not.toBeNull();
    expect(match?.lineIndex).toBe(0);
    expect(match?.noteIndex).toBe(0);
  });

  it('does not match wrong fret within tolerance', () => {
    const expectedNotes: TabNote[] = [
      { string: 6, fret: 3, timestamp: 0 }
    ];
    const match = findBestNoteMatch(detectedNote, expectedNotes, 25);
    expect(match).toBeNull();
  });
});
```

- [ ] **Step 2:** Run tests to verify they fail

Run: `npm test -- src/utils/__tests__/noteMatching.test.ts`
Expected: FAIL (functions not defined)

- [ ] **Step 3:** Implement `getNoteFrequency` and `findBestNoteMatch`

```typescript
// src/utils/noteMatching.ts
import { TabNote, NOTE_FREQUENCIES } from '../types';

// Get string frequencies for standard tuning EADGBE (6th to 1st string)
const STRING_OPEN_FREQUENCIES = [82.41, 110.00, 146.83, 196.00, 246.94, 329.63];

/**
 * Calculate frequency of a fretted note on a given string
 * fret 0 = open string frequency
 * Each fret adds 2^(1/12) factor
 */
export function getNoteFrequency(stringNumber: number, fret: number): number {
  // stringNumber: 1-6 (1=high E, 6=low E)
  // Map to open frequency array (index 0 = low E)
  const openFreq = STRING_OPEN_FREQUENCIES[6 - stringNumber];
  const semitones = fret;
  return openFreq * Math.pow(2, semitones / 12);
}

/**
 * Find the best matching expected note for a detected note
 * Returns null if no match within tolerance
 */
export function findBestNoteMatch(
  detected: TabNote,
  expectedNotes: TabNote[],
  toleranceCents: number = 25
): { lineIndex: number; noteIndex: number } | null {
  const detectedFreq = getNoteFrequency(detected.string, detected.fret);

  for (let lineIdx = 0; lineIdx < expectedNotes.length; lineIdx++) {
    const line = expectedNotes[lineIdx];
    for (let noteIdx = 0; noteIdx < line.notes.length; noteIdx++) {
      const expected = line.notes[noteIdx];
      const expectedFreq = getNoteFrequency(expected.string, expected.fret);

      // Calculate pitch deviation in cents
      const ratio = detectedFreq / expectedFreq;
      const cents = 1200 * Math.log2(ratio);

      if (Math.abs(cents) <= toleranceCents) {
        return { lineIndex: lineIdx, noteIndex: noteIdx };
      }
    }
  }

  return null;
}

/**
 * Get expected notes at or near a timestamp position
 * Returns notes within ±lookaheadMs window
 */
export function getExpectedNotesAt(
  lines: TabNote[][],
  position: number,
  lookaheadMs: number = 100
): { lineIndex: number; noteIndex: number; note: TabNote }[] {
  const results: { lineIndex: number; noteIndex: number; note: TabNote }[] = [];

  // Simplified: position is line index for now
  const currentLine = Math.floor(position);
  const nextLine = currentLine + 1;

  for (let i = currentLine; i <= nextLine && i < lines.length; i++) {
    const line = lines[i];
    for (let j = 0; j < line.length; j++) {
      const note = line[j];
      // For MVP: accept all notes at or after current position
      if (i >= currentLine) {
        results.push({ lineIndex: i, noteIndex: j, note });
      }
    }
  }

  return results;
}
```

- [ ] **Step 4:** Run tests to verify they pass

Run: `npm test -- src/utils/__tests__/noteMatching.test.ts`
Expected: PASS

- [ ] **Step 5:** Commit note matching utility

```bash
git add src/utils/noteMatching.ts src/utils/__tests__/noteMatching.test.ts
git commit -m "feat: add note matching algorithm"
```

---

### Task 3: Implement Scroll Controller

**Files:**
- Create: `src/utils/scrollController.ts`
- Test: `src/utils/__tests__/scrollController.test.ts`

**Steps:**

- [ ] **Step 1:** Write failing tests for scroll position management

```typescript
// src/utils/__tests__/scrollController.test.ts
import { createScrollController } from '../scrollController';

describe('ScrollController', () => {
  it('initializes at position 0', () => {
    const controller = createScrollController({ totalLines: 10 });
    expect(controller.getPosition()).toBe(0);
  });

  it('advances position at configured interval', () => {
    const controller = createScrollController({
      totalLines: 10,
      scrollRateMs: 1000 // 1 second per line
    });

    controller.start();
    // Simulate time passing would require mocking requestAnimationFrame
  });
});
```

- [ ] **Step 2:** Run tests to confirm failure

Expected: FAIL (not defined)

- [ ] **Step 3:** Implement scroll controller using requestAnimationFrame

```typescript
// src/utils/scrollController.ts
export interface ScrollControllerOptions {
  totalLines: number;
  scrollRateMs: number; // ms per line
  onPositionChange: (position: number) => void;
  onComplete: () => void;
}

export function createScrollController(options: ScrollControllerOptions) {
  let position = 0;
  let animationFrame: number | null = null;
  let lastTimestamp = 0;
  let isRunning = false;

  const animate = (timestamp: number) => {
    if (!lastTimestamp) lastTimestamp = timestamp;
    const elapsed = timestamp - lastTimestamp;

    if (elapsed >= options.scrollRateMs) {
      position += 1;
      options.onPositionChange(position);
      lastTimestamp = timestamp;

      if (position >= options.totalLines) {
        stop();
        options.onComplete();
        return;
      }
    }

    if (isRunning) {
      animationFrame = requestAnimationFrame(animate);
    }
  };

  const start = () => {
    if (isRunning) return;
    isRunning = true;
    lastTimestamp = 0;
    animationFrame = requestAnimationFrame(animate);
  };

  const pause = () => {
    isRunning = false;
    if (animationFrame) {
      cancelAnimationFrame(animationFrame);
      animationFrame = null;
    }
  };

  const stop = () => {
    pause();
    position = 0;
    lastTimestamp = 0;
    options.onPositionChange(0);
  };

  const setPosition = (pos: number) => {
    position = Math.max(0, Math.min(pos, options.totalLines - 1));
    options.onPositionChange(position);
  };

  const getPosition = () => position;

  return { start, pause, stop, setPosition, getPosition };
}
```

- [ ] **Step 4:** Run tests (may need to mock requestAnimationFrame)

```bash
npm test -- src/utils/__tests__/scrollController.test.ts
```

- [ ] **Step 5:** Commit scroll controller

```bash
git add src/utils/scrollController.ts src/utils/__tests__/scrollController.test.ts
git commit -m "feat: add scroll controller utility"
```

---

## Chunk 2: Enhanced TabViewer Component

### Task 4: Update TabViewer to Support Highlighting and Scroll

**Files:**
- Modify: `src/components/TabViewer.tsx`
- Test: `src/components/__tests__/TabViewer.test.tsx` (create or update)

**Steps:**

- [ ] **Step 1:** Update TabViewerProps to accept highlights and position

```typescript
// In TabViewer.tsx, update interface:
interface TabViewerProps {
  tab: Tab;
  currentLine: number; // 0-indexed line number
  highlightedNotes: HighlightedNote[];
  scrollContainerRef?: React.RefObject<HTMLDivElement>;
  // Keep existing difficulty, isPlaying, onPlayPause props - these will move to wrapper
}

// We'll eventually move play/pause to wrapper, but keep for now
```

- [ ] **Step 2:** Write test for TabViewer highlighting behavior

```typescript
// src/components/__tests__/TabViewer.test.tsx
import { render, screen } from '@testing-library/react';
import TabViewer from '../TabViewer';
import { Tab } from '../../types';

const mockTab: Tab = {
  id: '1',
  title: 'Test Song',
  artist: 'Test Artist',
  difficulty: 'easy',
  lines: [
    { measure: 1, notes: [{ string: 6, fret: 0, timestamp: 0 }] },
    { measure: 2, notes: [{ string: 6, fret: 2, timestamp: 1 }] }
  ]
};

describe('TabViewer', () => {
  it('renders tab lines', () => {
    render(<TabViewer tab={mockTab} currentLine={0} highlightedNotes={[]} />);
    expect(screen.getByText('1')).toBeInTheDocument(); // measure number
    expect(screen.getByText('2')).toBeInTheDocument();
  });

  it('applies current class to active line', () => {
    render(<TabViewer tab={mockTab} currentLine={1} highlightedNotes={[]} />);
    const lines = document.querySelectorAll('.tab-line');
    expect(lines[1]).toHaveClass('current');
  });
});
```

- [ ] **Step 3:** Update TabViewer to use line indices and highlight notes

```tsx
// src/components/TabViewer.tsx (partial update)
const TabViewer: React.FC<TabViewerProps> = ({
  tab,
  currentLine,
  highlightedNotes,
  scrollContainerRef,
  // other props...
}) => {
  // ... existing props handling

  const getNoteStatus = (lineIndex: number, noteIndex: number): string => {
    const highlight = highlightedNotes.find(
      hn => hn.lineIndex === lineIndex && hn.noteIndex === noteIndex
    );
    return highlight ? highlight.status : 'pending';
  };

  return (
    <div className="tab-viewer">
      <h3>{tab.title} - {tab.artist}</h3>
      <div className="tab-content" ref={scrollContainerRef}>
        {tab.lines.map((line, index) => (
          <div
            key={index}
            className={`tab-line ${index === currentLine ? 'current' : ''}`}
            data-line-index={index}
          >
            <span className="measure">{line.measure}</span>
            {line.notes.map((note, noteIndex) => {
              const status = getNoteStatus(index, noteIndex);
              return (
                <span
                  key={noteIndex}
                  className={`fret ${status} ${note.fret === 0 ? 'open' : ''} ${note.isChord ? 'chord' : ''}`}
                >
                  {note.fret === 0 ? '0' : note.fret}
                </span>
              );
            })}
          </div>
        ))}
      </div>
    </div>
  );
};
```

- [ ] **Step 4:** Run tests and fix any failures

```bash
npm test -- src/components/__tests__/TabViewer.test.tsx
```

- [ ] **Step 5:** Commit updated TabViewer

```bash
git add src/components/TabViewer.tsx src/components/__tests__/TabViewer.test.tsx
git commit -m "feat: update TabViewer with highlighting and current line support"
```

---

## Chunk 3: TabPlayer Container Component

### Task 5: Create TabPlayer with State Management

**Files:**
- Create: `src/components/TabPlayer.tsx`
- Test: `src/components/__tests__/TabPlayer.test.tsx`

**Steps:**

- [ ] **Step 1:** Write failing test for TabPlayer basic functionality

```typescript
// src/components/__tests__/TabPlayer.test.tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import TabPlayer from '../TabPlayer';
import { Tab } from '../../types';

const mockTab: Tab = {
  id: '1',
  title: 'Test Song',
  artist: 'Test Artist',
  difficulty: 'easy',
  lines: [
    { measure: 1, notes: [{ string: 6, fret: 0, timestamp: 0 }] },
    { measure: 2, notes: [{ string: 6, fret: 2, timestamp: 1 }] },
    { measure: 3, notes: [{ string: 6, fret: 3, timestamp: 2 }] }
  ]
};

describe('TabPlayer', () => {
  it('renders tab and controls', () => {
    render(<TabPlayer tab={mockTab} />);
    expect(screen.getByText('Test Song')).toBeInTheDocument();
    expect(screen.getByLabelText(/play/i)).toBeInTheDocument();
  });

  it('starts playback when play button clicked', async () => {
    render(<TabPlayer tab={mockTab} />);
    const playButton = screen.getByLabelText(/play/i);
    fireEvent.click(playButton);
    await waitFor(() => {
      expect(screen.getByLabelText(/pause/i)).toBeInTheDocument();
    });
  });
});
```

- [ ] **Step 2:** Implement basic TabPlayer with play/pause

```tsx
// src/components/TabPlayer.tsx
import React, { useState, useRef, useCallback, useEffect } from 'react';
import { Tab, PlayerSettings, HighlightedNote, PlayerMetrics } from '../types';
import TabViewer from './TabViewer';
import AutoscrollCtrl from './AutoscrollCtrl';
import TabPlayerSettings from './TabPlayerSettings';
import AudioFeedbackPanel from './AudioFeedbackPanel';
import { useAudioCapture } from '../hooks/useAudioCapture';
import { createScrollController } from '../utils/scrollController';
import { findBestNoteMatch, getExpectedNotesAt } from '../utils/noteMatching';

interface TabPlayerProps {
  tab: Tab;
}

const defaultSettings: PlayerSettings = {
  stopOnMistake: true,
  pitchTolerance: 25,
  scrollMode: 'auto',
  autoScrollSpeed: 120 // BPM equivalent
};

export const TabPlayer: React.FC<TabPlayerProps> = ({ tab }) => {
  const [status, setStatus] = useState<'stopped' | 'playing' | 'paused' | 'stopped-on-mistake'>('stopped');
  const [currentLine, setCurrentLine] = useState(0);
  const [settings, setSettings] = useState<PlayerSettings>(defaultSettings);
  const [metrics, setMetrics] = useState<PlayerMetrics>({
    totalNotesPlayed: 0,
    correctNotes: 0,
    incorrectNotes: 0,
    avgPitchDeviation: 0,
    startTime: null,
    elapsedTime: 0
  });
  const [highlights, setHighlights] = useState<HighlightedNote[]>([]);
  const [audioError, setAudioError] = useState<string | null>(null);

  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const scrollControllerRef = useRef<ReturnType<typeof createScrollController> | null>(null);

  // Audio capture
  const {
    startListening,
    stopListening,
    isListening,
    detectedNotes,
    error: audioErrorFromHook
  } = useAudioCapture({
    onNoteDetected: (note) => handleNoteDetected(note),
    onError: (err) => setAudioError(err.message)
  });

  // Initialize scroll controller
  useEffect(() => {
    scrollControllerRef.current = createScrollController({
      totalLines: tab.lines.length,
      scrollRateMs: 60000 / settings.autoScrollSpeed, // BPM to ms per line (simplified)
      onPositionChange: (pos) => {
        const lineIndex = Math.floor(pos);
        if (lineIndex !== currentLine) {
          setCurrentLine(lineIndex);
          scrollToLine(lineIndex);
        }
      },
      onComplete: () => {
        setStatus('stopped');
        stopListening();
      }
    });

    return () => {
      scrollControllerRef.current?.stop();
    };
  }, [tab.lines.length, settings.autoScrollSpeed]);

  // Handle audio note detection
  const handleNoteDetected = useCallback((detectedNote: any) => {
    if (status !== 'playing') return;

    const expectedNotes = getExpectedNotesAt(
      tab.lines.map(l => l.notes),
      currentLine,
      200 // lookahead ms
    );

    if (expectedNotes.length === 0) {
      // Extra note - incorrect
      setMetrics(prev => ({
        ...prev,
        totalNotesPlayed: prev.totalNotesPlayed + 1,
        incorrectNotes: prev.incorrectNotes + 1
      }));
      setHighlights(prev => [...prev, {
        lineIndex: currentLine,
        noteIndex: -1,
        status: 'incorrect'
      }]);
      if (settings.stopOnMistake) {
        stopPlayback();
      }
      return;
    }

    const match = findBestNoteMatch(
      detectedNote,
      expectedNotes.map(e => e.note),
      settings.pitchTolerance
    );

    if (match) {
      // Correct
      setMetrics(prev => ({
        ...prev,
        totalNotesPlayed: prev.totalNotesPlayed + 1,
        correctNotes: prev.correctNotes + 1
      }));
      setHighlights(prev => [...prev, {
        lineIndex: match.lineIndex,
        noteIndex: match.noteIndex,
        status: 'correct'
      }]);

      // Advance if auto
      if (settings.scrollMode === 'auto') {
        scrollControllerRef.current?.advance?.();
      }
    } else {
      // Wrong note
      setMetrics(prev => ({
        ...prev,
        totalNotesPlayed: prev.totalNotesPlayed + 1,
        incorrectNotes: prev.incorrectNotes + 1
      }));
      setHighlights(prev => [...prev, {
        lineIndex: currentLine,
        noteIndex: -1,
        status: 'incorrect'
      }]);
      if (settings.stopOnMistake) {
        stopPlayback();
      }
    }
  }, [status, currentLine, settings]);

  const scrollToLine = (lineIndex: number) => {
    const container = scrollContainerRef.current;
    if (container) {
      const lineElement = container.querySelector(`[data-line-index="${lineIndex}"]`);
      lineElement?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  };

  const play = async () => {
    if (status === 'stopped' || status === 'stopped-on-mistake') {
      setCurrentLine(0);
      setHighlights([]);
      setMetrics({
        totalNotesPlayed: 0,
        correctNotes: 0,
        incorrectNotes: 0,
        avgPitchDeviation: 0,
        startTime: Date.now(),
        elapsedTime: 0
      });
    }

    setStatus('playing');
    await startListening();
    scrollControllerRef.current?.start();
  };

  const pause = () => {
    setStatus('paused');
    scrollControllerRef.current?.pause();
    stopListening();
  };

  const stop = () => {
    setStatus('stopped');
    scrollControllerRef.current?.stop();
    stopListening();
    setCurrentLine(0);
    scrollToLine(0);
  };

  const stopOnMistake = () => {
    setStatus('stopped-on-mistake');
    scrollControllerRef.current?.stop();
    stopListening();
  };

  const updateSettings = (newSettings: Partial<PlayerSettings>) => {
    setSettings(prev => ({ ...prev, ...newSettings }));
  };

  return (
    <div className="tab-player">
      <div className="tab-viewer">
        <div className="current-line-indicator" />
        <div className="tab-content" ref={scrollContainerRef}>
          <TabViewer
            tab={tab}
            currentLine={currentLine}
            highlightedNotes={highlights}
          />
        </div>
        <div className="player-info">
          <span>Line: {currentLine + 1} / {tab.lines.length}</span>
          <span>Status: {status}</span>
          <span>Accuracy: {metrics.totalNotesPlayed > 0
            ? Math.round((metrics.correctNotes / metrics.totalNotesPlayed) * 100)
            : 100}%</span>
        </div>
        <div className="progress-bar">
          <div
            className="progress-fill"
            style={{ width: `${(currentLine / tab.lines.length) * 100}%` }}
          />
        </div>
      </div>

      <AutoscrollCtrl
        isPlaying={status === 'playing'}
        currentPosition={currentLine}
        totalLines={tab.lines.length}
        onPlay={play}
        onPause={pause}
        onStop={stop}
        speed={settings.autoScrollSpeed}
        onSpeedChange={(speed) => updateSettings({ autoScrollSpeed: speed })}
      />

      <TabPlayerSettings
        settings={settings}
        onSettingsChange={updateSettings}
      />

      <AudioFeedbackPanel
        recentNotes={[]} // TODO: implement recent notes from detectedNotes
        metrics={metrics}
      />

      {audioError && (
        <div className="error-banner">
          <span>{audioError}</span>
          <button onClick={() => setAudioError(null)}>✕</button>
        </div>
      )}
    </div>
  );
};
```

- [ ] **Step 3:** Run tests, they should fail initially

```bash
npm test -- src/components/__tests__/TabPlayer.test.tsx
```

- [ ] **Step 4:** Gradually flesh out implementation to pass tests
  - Add missing imports
  - Implement child component interfaces
  - Fix state management issues

- [ ] **Step 5:** Commit TabPlayer with stubs for child components

```bash
git add src/components/TabPlayer.tsx src/components/__tests__/TabPlayer.test.tsx
git commit -m "feat: add TabPlayer container component with basic state"
```

---

## Chunk 4: Child Components - Settings and Feedback

### Task 6: Implement TabPlayerSettings

**Files:**
- Create: `src/components/TabPlayerSettings.tsx`

**Steps:**

- [ ] **Step 1:** Implement settings UI with toggles

```tsx
// src/components/TabPlayerSettings.tsx
import React from 'react';
import { PlayerSettings } from '../types';

interface TabPlayerSettingsProps {
  settings: PlayerSettings;
  onSettingsChange: (newSettings: Partial<PlayerSettings>) => void;
}

const TabPlayerSettings: React.FC<TabPlayerSettingsProps> = ({
  settings,
  onSettingsChange
}) => {
  return (
    <div className="settings-panel">
      <h3>Settings</h3>

      <div className="setting-item">
        <label>Stop on Mistake</label>
        <div
          className={`toggle ${settings.stopOnMistake ? 'active' : ''}`}
          onClick={() => onSettingsChange({ stopOnMistake: !settings.stopOnMistake })}
          role="switch"
          aria-checked={settings.stopOnMistake}
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              onSettingsChange({ stopOnMistake: !settings.stopOnMistake });
            }
          }}
        >
          <span className="label">Stop</span>
          <span className={`status ${settings.stopOnMistake ? 'on' : 'off'}`}>
            {settings.stopOnMistake ? 'ON' : 'OFF'}
          </span>
        </div>
      </div>

      <div className="setting-item">
        <label>Pitch Tolerance: ±{settings.pitchTolerance} cents</label>
        <input
          type="range"
          min="10"
          max="50"
          step="5"
          value={settings.pitchTolerance}
          onChange={(e) => onSettingsChange({ pitchTolerance: Number(e.target.value) })}
        />
      </div>

      <div className="setting-item">
        <label>Scroll Mode</label>
        <div className="mode-buttons">
          <button
            className={settings.scrollMode === 'auto' ? 'active' : ''}
            onClick={() => onSettingsChange({ scrollMode: 'auto' })}
          >
            Auto
          </button>
          <button
            className={settings.scrollMode === 'manual' ? 'active' : ''}
            onClick={() => onSettingsChange({ scrollMode: 'manual' })}
          >
            Manual
          </button>
        </div>
      </div>
    </div>
  );
};

export default TabPlayerSettings;
```

- [ ] **Step 2:** Add CSS styles to App.css

```css
/* Add to App.css */
.settings-panel {
  width: 300px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  padding: 1.5rem;
  backdrop-filter: blur(20px);
}

.settings-panel h3 {
  margin-bottom: 1rem;
  color: #4ecdc4;
  text-align: center;
  font-size: 1.2rem;
}

.setting-item {
  margin-bottom: 1rem;
}

.setting-item label {
  display: block;
  margin-bottom: 0.5rem;
  color: #ccc;
  font-weight: bold;
  text-transform: uppercase;
  font-size: 0.8rem;
  letter-spacing: 0.5px;
}

.setting-item .toggle {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.setting-item .toggle:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(255, 255, 255, 0.2);
}

.setting-item .toggle.active {
  background: rgba(78, 205, 196, 0.2);
  border-color: rgba(78, 205, 196, 0.4);
}

.setting-item .toggle .label {
  color: #fff;
  font-weight: bold;
}

.setting-item .toggle .status {
  color: #4ecdc4;
  font-weight: bold;
}

.setting-item .toggle .status.off {
  color: #ff6b6b;
}

.setting-item .mode-buttons {
  display: flex;
  gap: 0.5rem;
}

.setting-item .mode-buttons button {
  flex: 1;
  padding: 0.5rem;
  border: 1px solid rgba(255, 255, 255, 0.2);
  background: rgba(255, 255, 255, 0.05);
  color: #ccc;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.setting-item .mode-buttons button.active {
  background: rgba(78, 205, 196, 0.2);
  border-color: rgba(78, 205, 196, 0.4);
  color: #fff;
}
```

- [ ] **Step 3:** Commit TabPlayerSettings

```bash
git add src/components/TabPlayerSettings.tsx
git commit -m "feat: add TabPlayerSettings component"
```

---

### Task 7: Implement AudioFeedbackPanel

**Files:**
- Create: `src/components/AudioFeedbackPanel.tsx`

**Steps:**

- [ ] **Step 1:** Implement panel showing recent notes and accuracy

```tsx
// src/components/AudioFeedbackPanel.tsx
import React from 'react';
import { DetectedNote, PlayerMetrics } from '../types';

interface AudioFeedbackPanelProps {
  recentNotes: DetectedNote[];
  metrics: PlayerMetrics;
}

const AudioFeedbackPanel: React.FC<AudioFeedbackPanelProps> = ({
  recentNotes,
  metrics
}) => {
  const accuracy = metrics.totalNotesPlayed > 0
    ? Math.round((metrics.correctNotes / metrics.totalNotesPlayed) * 100)
    : 100;

  return (
    <div className="audio-feedback">
      <h4>Audio Feedback</h4>
      <div className="feedback-stats">
        <span>Accuracy: {accuracy}%</span>
        <span>✓ {metrics.correctNotes}</span>
        <span>✗ {metrics.incorrectNotes}</span>
      </div>
      <div className="feedback-list">
        {recentNotes.slice(-5).reverse().map((detected, idx) => (
          <div key={idx} className="feedback-item">
            <span className="note-info">
              String {detected.note.string} - Fret {detected.note.fret}
            </span>
            <span className={`status ${detected.pitchDeviation !== undefined && Math.abs(detected.pitchDeviation) > 25 ? 'incorrect' : 'correct'}`}>
              {detected.pitchDeviation !== undefined && Math.abs(detected.pitchDeviation) > 25 ? 'Off' : 'Good'}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default AudioFeedbackPanel;
```

- [ ] **Step 2:** Add CSS for feedback panel (add to earlier styles)

```css
.audio-feedback {
  margin-top: 1rem;
  padding: 1rem;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 6px;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.audio-feedback h4 {
  margin-bottom: 0.5rem;
  color: #4ecdc4;
  font-size: 1rem;
}

.feedback-stats {
  display: flex;
  gap: 1rem;
  margin-bottom: 0.5rem;
}

.feedback-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.feedback-item:last-child {
  border-bottom: none;
}

.feedback-item .note-info {
  flex: 1;
  color: #ccc;
}

.feedback-item .status {
  font-weight: bold;
}

.feedback-item .status.correct {
  color: #4ecdc4;
}

.feedback-item .status.incorrect {
  color: #ff6b6b;
}
```

- [ ] **Step 3:** Commit AudioFeedbackPanel

```bash
git add src/components/AudioFeedbackPanel.tsx
git commit -m "feat: add AudioFeedbackPanel component"
```

---

## Chunk 5: AutoscrollCtrl Component and Wiring

### Task 8: Implement AutoscrollCtrl

**Files:**
- Create: `src/components/AutoscrollCtrl.tsx`
- Test: `src/components/__tests__/AutoscrollCtrl.test.tsx`

**Steps:**

- [ ] **Step 1:** Write test for control functionality

```typescript
// src/components/__tests__/AutoscrollCtrl.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import AutoscrollCtrl from '../AutoscrollCtrl';

describe('AutoscrollCtrl', () => {
  const defaultProps = {
    isPlaying: false,
    currentPosition: 0,
    totalLines: 10,
    onPlay: jest.fn(),
    onPause: jest.fn(),
    onStop: jest.fn(),
    onSpeedChange: jest.fn(),
    speed: 120
  };

  it('shows play button when not playing', () => {
    render(<AutoscrollCtrl {...defaultProps} />);
    expect(screen.getByLabelText(/play/i)).toBeInTheDocument();
  });

  it('calls onPlay when play clicked', () => {
    render(<AutoscrollCtrl {...defaultProps} />);
    fireEvent.click(screen.getByLabelText(/play/i));
    expect(defaultProps.onPlay).toHaveBeenCalled();
  });
});
```

- [ ] **Step 2:** Implement AutoscrollCtrl

```tsx
// src/components/AutoscrollCtrl.tsx
import React from 'react';

interface AutoscrollCtrlProps {
  isPlaying: boolean;
  currentPosition: number;
  totalLines: number;
  onPlay: () => void;
  onPause: () => void;
  onStop: () => void;
  speed: number;
  onSpeedChange: (speed: number) => void;
}

const AutoscrollCtrl: React.FC<AutoscrollCtrlProps> = ({
  isPlaying,
  currentPosition,
  totalLines,
  onPlay,
  onPause,
  onStop,
  speed,
  onSpeedChange
}) => {
  return (
    <div className="autoscroll-controls">
      <div className="speed-control">
        <label htmlFor="scroll-speed">Speed (BPM):</label>
        <input
          id="scroll-speed"
          type="range"
          min="60"
          max="180"
          value={speed}
          onChange={(e) => onSpeedChange(Number(e.target.value))}
        />
        <span>{speed} BPM</span>
      </div>

      <button
        onClick={isPlaying ? onPause : onPlay}
        aria-label={isPlaying ? 'Pause' : 'Play'}
        className={isPlaying ? 'active' : ''}
      >
        {isPlaying ? '⏸ Pause' : '▶ Play'}
      </button>

      <button
        onClick={onStop}
        aria-label="Stop"
        disabled={!isPlaying && currentPosition === 0}
      >
        ⏹ Stop
      </button>

      <div className="player-status">
        Status: <strong>{isPlaying ? 'Playing' : 'Stopped'}</strong>
      </div>
    </div>
  );
};

export default AutoscrollCtrl;
```

- [ ] **Step 3:** Commit AutoscrollCtrl

```bash
git add src/components/AutoscrollCtrl.tsx src/components/__tests__/AutoscrollCtrl.test.tsx
git commit -m "feat: add AutoscrollCtrl component"
```

---

### Task 9: Integrate TabPlayer into App and Remove Old Components

**Files:**
- Modify: `src/App.tsx`
- Modify: `src/App.css` (reuse existing styles)
- Delete (optional): `src/components/Autoscroll.tsx` (old version)

**Steps:**

- [ ] **Step 1:** Update App.tsx to use TabPlayer instead of separated components

```tsx
// src/App.tsx
import { useState } from 'react';
import { Tab, Difficulty } from './types';
import { searchTabs } from './api/search';
import TabPlayer from './components/TabPlayer';
import SearchBar from './components/SearchBar';
import DifficultyPicker from './components/DifficultyPicker';
import './App.css';

function App() {
  const [tabs, setTabs] = useState<Tab[]>([]);
  const [selectedTab, setSelectedTab] = useState<Tab | null>(null);
  const [difficulty, setDifficulty] = useState<Difficulty>('easy');

  const handleSearch = async (query: string) => {
    try {
      const results = await searchTabs(query, difficulty);
      setTabs(results.tabs);
    } catch (error) {
      console.error('Search failed:', error);
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>Guitar Tab Learner</h1>
      </header>
      <main>
        <SearchBar onSearch={handleSearch} />
        <DifficultyPicker
          value={difficulty}
          onChange={setDifficulty}
        />
        <div className="tabs-grid">
          {tabs.map((tab) => (
            <div key={tab.id} className="tab-card" onClick={() => setSelectedTab(tab)}>
              <h3>{tab.title}</h3>
              <p>{tab.artist}</p>
              <span className="difficulty-badge">{tab.difficulty}</span>
            </div>
          ))}
        </div>
        {selectedTab && (
          <TabPlayer tab={selectedTab} />
        )}
      </main>
    </div>
  );
}

export default App;
```

- [ ] **Step 2:** Remove references to old Autoscroll component if still imported

```bash
# Check if any imports or references remain
grep -r "Autoscroll" src/App.tsx src/components/
```

- [ ] **Step 3:** Delete old Autoscroll.tsx file (optional, keep for reference)

```bash
rm src/components/Autoscroll.tsx
# Or move to backup if you want to keep it
```

- [ ] **Step 4:** Run dev server and test basic functionality

```bash
npm run dev
```

- [ ] **Step 5:** Commit integration

```bash
git add src/App.tsx
git commit -m "feat: integrate TabPlayer into main app; remove old Autoscroll"
```

---

## Chunk 6: Audio Integration Enhancements

### Task 10: Enhance useAudioCapture Hook

**Files:**
- Modify: `src/hooks/useAudioCapture.ts`

**Steps:**

- [ ] **Step 1:** Update hook to include pitch deviation calculation

```typescript
// In useAudioCapture.ts, modify the callback
import { computePitchDeviation } from '../utils/noteMatching';

// Inside detectPitch callback:
detectPitch(analyserRef.current, (pitch: number, time: number) => {
  if (pitch > 0) {
    const note = detectNote(pitch);
    if (note) {
      const tabNote: TabNote = {
        string: 0, // TODO: determine actual string from frequency
        fret: note.fret,
        timestamp: time,
        duration: 0.5
      };

      // Calculate deviation if we have expected note (will be passed from parent)
      // For now, just pass the detected note
      setDetectedNotes(prev => [...prev, tabNote]);
      onNoteDetected(tabNote);
    }
  }
});
```

- [ ] **Step 2:** Add function to estimate string from frequency (simplified)

```typescript
// In noteMatching.ts or new utils file
export function estimateStringFromFrequency(frequency: number): number {
  const STRING_OPEN_FREQUENCIES = [82.41, 110.00, 146.83, 196.00, 246.94, 329.63];
  let bestString = 1;
  let bestDiff = Infinity;

  for (let i = 0; i < STRING_OPEN_FREQUENCIES.length; i++) {
    // Check if frequency is within playable range of this string (open to ~22nd fret)
    const openFreq = STRING_OPEN_FREQUENCIES[i];
    const maxFreq = openFreq * Math.pow(2, 22 / 12);
    if (frequency >= openFreq && frequency <= maxFreq) {
      const diff = Math.abs(frequency - openFreq);
      if (diff < bestDiff) {
        bestDiff = diff;
        bestString = i + 1; // 1-indexed
      }
    }
  }

  return bestString;
}
```

Then in hook, use this to set the string number:

```typescript
const stringNumber = estimateStringFromFrequency(pitch);
tabNote.string = stringNumber;
```

- [ ] **Step 3:** Commit enhanced audio hook

```bash
git add src/hooks/useAudioCapture.ts src/utils/noteMatching.ts
git commit -m "feat: enhance audio capture with string estimation"
```

---

### Task 11: Complete Audio-Triggered Playback Logic

**Files:**
- Modify: `src/components/TabPlayer.tsx`

**Steps:**

- [ ] **Step 1:** Wire detected notes from useAudioCapture to handleNoteDetected

Already done in earlier TabPlayer, but ensure proper passing

- [ ] **Step 2:** Implement proper note-to-note matching with timing

Update `handleNoteDetected`:
- Maintain a buffer of recently detected notes
- Compare against expected notes with timestamp lookahead
- Deduplicate detections (same note within 100ms)

- [ ] **Step 3:** Add visual feedback for detected notes

Update state to include `detectedNotes` array and display in AudioFeedbackPanel

```tsx
const [detectedNotes, setDetectedNotes] = useState<DetectedNote[]>([]);

// In handleNoteDetected, after validation:
setDetectedNotes(prev => [...prev.slice(-10), { note: detectedNote, pitch, timestamp: Date.now(), confidence: 0.9 }]);
```

Pass `detectedNotes` to `<AudioFeedbackPanel recentNotes={detectedNotes} ... />`

- [ ] **Step 4:** Commit refined audio integration

```bash
git add src/components/TabPlayer.tsx
git commit -m "feat: complete audio-triggered playback with detection buffer"
```

---

## Chunk 7: Polish, Error Handling, and Accessibility

### Task 12: Add Error Boundaries and Loading States

**Files:**
- Modify: `src/App.tsx` (add error handling)
- Create: `src/components/ErrorBoundary.tsx` (optional)

**Steps:**

- [ ] **Step 1:** Add error state handling in App

```tsx
// In App.tsx
const [error, setError] = useState<string | null>(null);

const handleSearch = async (query: string) => {
  try {
    setError(null);
    const results = await searchTabs(query, difficulty);
    setTabs(results.tabs);
  } catch (err) {
    setError('Failed to search tabs. Please try again.');
  }
};
```

- [ ] **Step 2:** Display error banner if error exists

```tsx
{error && (
  <div className="error-banner">
    <span>{error}</span>
    <button onClick={() => setError(null)}>✕</button>
  </div>
)}
```

- [ ] **Step 3:** Add loading state during search

```tsx
const [isSearching, setIsSearching] = useState(false);

const handleSearch = async (query: string) => {
  setIsSearching(true);
  try {
    // ...
  } finally {
    setIsSearching(false);
  }
};

// In SearchBar, show spinner during search
```

- [ ] **Step 4:** Commit error handling improvements

```bash
git add src/App.tsx
git commit -m "feat: add error handling and loading states"
```

---

### Task 13: Accessibility Improvements

**Files:**
- Modify: All components as needed

**Steps:**

- [ ] **Step 1:** Add ARIA labels to buttons

Already partly done. Ensure all interactive elements have:
- `aria-label` where text is insufficient
- `role` attributes where needed
- `tabIndex` for custom interactive divs

- [ ] **Step 2:** Add keyboard shortcuts

In TabPlayer, add:

```tsx
useEffect(() => {
  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === ' ' || e.key === 'Spacebar') {
      e.preventDefault();
      if (status === 'playing') pause();
      else play();
    } else if (e.key === 'Escape') {
      e.preventDefault();
      stop();
    }
  };

  window.addEventListener('keydown', handleKeyDown);
  return () => window.removeEventListener('keydown', handleKeyDown);
}, [status, play, pause, stop]);
```

- [ ] **Step 3:** Ensure focus management in settings

Settings toggles should be focusable and respond to Enter/Space

- [ ] **Step 4:** Add aria-live regions for status updates

```tsx
<div aria-live="polite" className="sr-only">
  {status === 'playing' ? 'Playback started' : 'Playback stopped'}
</div>
```

- [ ] **Step 5:** Commit accessibility improvements

```bash
git add src/components/TabPlayer.tsx src/components/TabPlayerSettings.tsx
git commit -m "feat: add keyboard navigation and ARIA labels"
```

---

## Chunk 8: Testing Finalization

### Task 14: Write Comprehensive Integration Tests

**Files:**
- Create: `src/components/__tests__/TabPlayer.integration.test.tsx`

**Steps:**

- [ ] **Step 1:** Write test for full play -> note -> stop flow

```typescript
// src/components/__tests__/TabPlayer.integration.test.tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import TabPlayer from '../TabPlayer';
import { Tab } from '../../types';

const createMockTab = (): Tab => ({
  id: '1',
  title: 'Test',
  artist: 'Test',
  difficulty: 'easy',
  lines: Array(10).fill(null).map((_, i) => ({
    measure: i + 1,
    notes: [{ string: 6, fret: i % 5, timestamp: i }]
  }))
});

describe('TabPlayer Integration', () => {
  it('stops on mistake when setting enabled', async () => {
    const tab = createMockTab();
    // Mock useAudioCapture to simulate wrong note
    jest.spyOn(require('../../hooks/useAudioCapture'), 'useAudioCapture').mockReturnValue({
      startListening: jest.fn().mockResolvedValue(undefined),
      stopListening: jest.fn(),
      isListening: true,
      error: null,
      detectedNotes: []
    });

    render(<TabPlayer tab={tab} />);
    // Interact and assert
  });
});
```

- [ ] **Step 2:** Run all tests and fix failures

```bash
npm test
```

- [ ] **Step 3:** Ensure test coverage > 70% for new code

```bash
npm run test:coverage
```

- [ ] **Step 4:** Commit integration tests

```bash
git add src/components/__tests__/TabPlayer.integration.test.tsx
git commit -m "test: add integration tests for TabPlayer"
```

---

### Task 15: Final Manual Testing Checklist

**Manual Steps:**

- [ ] **Step 1:** Start dev server and open app

```bash
npm run dev
```

- [ ] **Step 2:** Test audio capture functionality
  - Allow microphone access
  - Play a guitar (or use tone generator)
  - Confirm notes are detected
  - Check highlighting

- [ ] **Step 3:** Test autoscroll modes
  - Auto scroll: should advance as notes are played correctly
  - Manual mode: scroll should not auto-advance
  - Stop on mistake: intentionally play wrong note and verify stop

- [ ] **Step 4:** Test all controls
  - Play/Pause button
  - Stop button (resets to beginning)
  - Speed slider (adjusts scroll rate)
  - Settings toggles (stop on mistake, tolerance)
  - All controls responsive

- [ ] **Step 5:** Verify responsive layout
  - Resize browser window
  - Check mobile view if applicable
  - Ensure panels stack appropriately

- [ ] **Step 6:** Check accessibility
  - Tab through controls
  - Use keyboard shortcuts (Space, Escape)
  - Verify screen reader announcements (if available)

---

## Chunk 9: Documentation and Cleanup

### Task 16: Update README and CLAUDE.md

**Files:**
- Modify: `README.md`
- Modify: `CLAUDE.md`

**Steps:**

- [ ] **Step 1:** Update README with new features

```markdown
## Features

- **Tab Display:** Clean ASCII tab notation with syntax highlighting
- **Autoscroll:** Automatically scrolls as you play
- **Audio Feedback:** Real-time note detection and accuracy tracking
- **Stop on Mistake:** Practice mode that halts playback on wrong notes
- **Customizable Settings:** Adjustable tolerance, speed, and behavior
- **Search:** Find tabs by song title/artist
- **Difficulty Levels:** Easy/Medium/Hard filtering
```

- [ ] **Step 2:** Update CLAUDE.md with architecture changes

```markdown
### Current State
- TabPlayer component with audio-driven autoscroll
- Real-time pitch detection and note validation
- Settings panel for practice customization
- Clean professional UI with dark theme
```

- [ ] **Step 3:** Commit documentation updates

```bash
git add README.md CLAUDE.md
git commit -m "docs: update with autoscroll and audio features"
```

---

### Task 17: Final Code Review and Refactoring

**Steps:**

- [ ] **Step 1:** Run ESLint and fix any warnings

```bash
npm run lint
```

- [ ] **Step 2:** Run TypeScript strict mode check

```bash
npx tsc --noEmit --strict
```

- [ ] **Step 3:** Review and remove any console.log statements

- [ ] **Step 4:** Ensure all TODOs are addressed or documented

- [ ] **Step 5:** Commit final cleanup

```bash
git add .
git commit -m "refactor: code review and cleanup"
```

---

## Summary

By following this plan, you will build a fully functional Tab Player with:

✅ Audio-driven autoscroll that advances on correct notes
✅ Real-time feedback highlighting (correct/incorrect)
✅ Stop-on-mistake practice mode
✅ Clean, professional UI with settings
✅ Comprehensive test coverage
✅ Accessible and keyboard-friendly
✅ Well-documented and maintainable code

---

## After Implementation

Once all tasks are complete:

1. Run full test suite: `npm test`
2. Build for production: `npm run build`
3. Verify build output: `npm run preview`
4. **Push to GitHub** (user reminder)

---

**Plan Version:** 1.0
**Last Updated:** 2025-03-15
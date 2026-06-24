# Boardom — V1 Design Spec

## Overview

Two strangers share an anonymous real-time canvas. No accounts, no chat, no video. Just a shared drawing space and two cursors. Sessions are fully ephemeral — when either person leaves, the canvas is gone.

The name: Board + Boredom.

---

## Screens

### Landing
- Wordmark: "Boardom"
- 18+ acknowledgment checkbox
- "Start" button (disabled until checkbox checked)
- No other UI

### Waiting
- "Finding someone..." copy + animation
- Cancel button → returns to Landing
- Timeout: if no match after 60 seconds, show "No one around right now, try again" and return to Landing

### Canvas
- Left sidebar: drawing tools
- Center: shared tldraw canvas
- Right sidebar: stickers / sticky notes / emoji
- Small "Leave" button, top corner, no confirmation

---

## Tech Stack

| Concern | Choice | Hosting |
|---|---|---|
| Frontend framework | Next.js | Vercel (free) |
| Canvas | tldraw | — |
| Matchmaking + signaling | Supabase Realtime | Supabase free tier |
| P2P data channel | simple-peer (WebRTC) | — |
| Database | None | — |
| Auth | None | — |

---

## Matchmaking Flow

1. User checks 18+ box and hits Start
2. Frontend generates a random UUID for this session
3. User joins Supabase Realtime channel `lobby` via Presence, broadcasting their UUID and join timestamp
4. When Presence shows 2+ users, the one with the **earlier join timestamp** becomes the initiator (tiebreaker: lower UUID string value)
5. Initiator creates a WebRTC offer (via simple-peer), sends it to the other user's UUID as a Supabase channel message
6. Responder receives offer, creates answer, sends it back
7. ICE candidates exchanged through the same channel
8. DataChannel established → both leave `lobby` channel → Canvas screen loads
9. 60-second timeout: if no second user appears in Presence, show retry message

---

## Canvas Sync

- tldraw's `store.listen()` captures every local change (stroke, shape, sticky note, cursor move) as a serializable diff
- Diff is sent over the WebRTC DataChannel to the partner
- Partner receives diff and applies it via `store.mergeRemoteChanges()`
- Cursor positions broadcast separately on `pointermove`, applied to tldraw's multiplayer cursor API
- Undo/erase is scoped to own strokes — tldraw enforces this natively

---

## Session End

- WebRTC DataChannel `close` event fires when either user disconnects or closes the tab
- The remaining user sees: "Your partner left." with a "Start again" button
- No save prompt, no replay, no gallery — fully ephemeral by design

---

## UI Detail

**Left sidebar — drawing tools:**
- Brush (freehand)
- Eraser (own strokes only)
- Color picker
- Stroke size slider
- Text tool (places editable text on canvas)
- Shape tool (rectangle, circle, arrow)

tldraw's default toolbar, restyled to match Boardom's visual identity.

**Right sidebar — stickers / notes / emoji:**
Three tabs:
- **Notes** — places a draggable sticky note on canvas (tldraw's built-in note shape)
- **Emoji** — grid of emoji stamps; tap to place at canvas center, then drag
- **Stickers** — small curated set of pre-drawn SVG stamps (e.g. thumbs up, star, heart, question mark)

All items in the right sidebar are tldraw shapes — they sync over the same DataChannel as drawings.

**Cursors:**
- Both cursors always visible
- No labels — you know which is yours by where it moves
- Rendered via tldraw's built-in multiplayer cursor support

---

## What's Explicitly Out of Scope for V1

- Save / gallery / replay
- Interaction modes (Doodle Relay, Guess & Draw, etc.)
- Language filtering
- Moderation / reporting
- Accounts or persistent identity
- Mobile-native app (web-first; touch works but not optimized)
- TURN server fallback for restrictive networks

# ABOUT.md

## Why this role

AgentCollect is solving a genuinely hard problem — automating
collections for Fortune 500 clients requires precision, compliance,
and reliability that most AI systems don't have. The fact that you
dogfood your own product and your founder reviews every PR tells me
the engineering culture matches how I like to work: high ownership,
low ceremony.

I use Claude Code and Cursor daily — not as autocomplete but as a
thinking partner. Your CLAUDE.md approach of encoding conventions
explicitly is something I'd adopt and contribute to immediately.

## How I work with AI tools

My workflow: describe the problem and constraints to Claude before
writing any code. The conversation surfaces assumptions I haven't
examined. I ask for implementation only after I understand the shape
of the solution. I read generated code before running it — if I
can't explain what it does, I don't ship it.

Biggest failure mode I've learned to catch: AI is confidently wrong
on domain-specific details. In my chess platform, Claude generated
legal move logic that missed en passant. I caught it with manual
game testing. I now write tests first, describe what they verify,
then ask for implementation that passes them.

## Last project: FineChess — AI chess coaching platform

**One ambiguity I faced:**
The goal was "make the AI coach feel like it understands the game."
That's not a spec — it's a feeling. The ambiguity: what does
"understands" mean technically? I spent two days passing raw
Stockfish UCI output directly to the LLM and getting generic
responses. The engine knew what happened. The LLM didn't know why
it mattered to this player, in this position. I had to reframe:
it wasn't a prompt engineering problem, it was a data structuring
problem. I built a translation layer that converts raw UCI into
structured per-move JSON before it touches the LLM.

**One tradeoff I made:**
ElevenLabs TTS sounded great but flagged Kenyan IPs on free tier.
Options: proxy through a VPN server I'd maintain, or switch to
Web Speech API and lose audio quality. I chose Web Speech API.
A coaching voice that sometimes fails is worse than a slightly
robotic one that always works. Shipped in an afternoon, never
broke again.

**One mistake I made:**
I built the RAG retrieval layer before I had real queries to test
against. Chunked the knowledge base at 350-word segments, built
the TF-IDF index, thought I was done. First real test: a user asks
about piece trades — the retriever pulled endgame pawn content.
Wrong. I was optimizing chunk size for storage, not query relevance.
Rebuilt chunking around concept boundaries. Retrieval quality jumped
immediately.

**One review comment that changed my mind:**
A senior engineer looked at my eval bar and said: "Why are you
using a linear scale? A +3 advantage with queens on the board is
completely different from +3 in an endgame." I'd been thinking
about it as a display problem. He made me see it was a domain
modeling problem. I switched to an atan-based compression function.
Changed how I think about representing domain-specific data in UI
permanently.

## What I'd improve about this challenge

The CLAUDE.md conventions file is excellent — it encodes exactly
the kind of implicit knowledge that kills onboarding time. One
suggestion: add a short section on how you handle the boundary
between "AI-generated first draft" and "engineer-owned code." The
conventions cover style but not the ownership question, which is
where most AI-assisted teams drift.
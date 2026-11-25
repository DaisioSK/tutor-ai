# tutor-ai

tutor-ai is a set of [Claude Code](https://docs.claude.com/en/docs/claude-code) skills that turn a course's lecture slides (PDF) into structured study material: a concept map with prerequisites, a teaching handout that tells the whole course as one story, worked-exercise breakdowns, and a printable exam cheat sheet. It is meant for a student who has to understand a dense course quickly and only has the slides to go on (no textbook, little time), and who wants every claim in the generated material to point back to a slide page they can check.

The skill instructions and the generated material are written in Chinese, with English technical terms kept alongside. The pipeline itself does not depend on the language of the slides.

## How it works

```
courses/<course>/*.pdf
        │
        ▼
  scan ──► concepts.json, course outline, coverage audit   (text extraction + concept map)
        │
        ├─► story        teaching handout: one narrative thread through all lectures (Markdown + PDF)
        ├─► teach <X>    explain one concept, with where it sits in the map and what it depends on
        ├─► quiz <X>     practice questions on one concept
        ├─► check        review notes you wrote yourself
        ├─► map          whole-course concept graph
        ├─► exam-prep    analyse past papers you supply, plus a core-ideas handout
        └─► cheatsheet   compact printable sheet for an open-book exam
```

Generated files go to `output/<course>/`.

### Skills

| Skill | What it does |
|---|---|
| `tutor` | The main entry point. Extracts slide text (`scripts/extract.py`, PyMuPDF with fallbacks), builds the concept map, and runs the commands above. Reference files under `references/` hold the instructions for each command; `scripts/` holds the PDF compilers and checkers. |
| `full-learn` | Writes a whole course up as a book that can be read front to back: builds a dependency tree of every concept, derives a reading path from it, writes chapters, then has a "cold reader" agent with no background read it and report where it got lost. Structured as modules (ingest, tree, spine, compose, audit, render), each with a method file (`PARADIGM.md`) and acceptance checks (`EXPECT.md`, `GATES.md`), plus verification scripts. |
| `story-cards` | Adapts a `full-learn` book into one story world (for example, a restaurant) told across the whole course, one card per section: the story on the left; on the right the technical points, how the metaphor maps onto the concept and where it breaks down, and a small worked calculation. Output is HTML plus a phone-sized PDF. |
| `drill-paradigm` | After you finish a practice problem, writes a short step-by-step "how to do this type of problem" summary at the end of the problem file and merges it into a single exercise cheat sheet. |

### Running it

Requirements: Claude Code, Python 3.8+. `extract.py` installs `pymupdf`, `python-docx` and `python-pptx` if they are missing. PDF output needs `markdown`, `weasyprint` and `pymdown-extensions`, plus a CJK font (Noto Sans CJK or similar).

1. Clone this repo and open it in Claude Code. The skills live in `.claude/skills/`, so they are picked up automatically.
2. Put the slides in `courses/<course>/`, for example `courses/operating-systems/`.
3. Run the commands from the repo root:

```
/tutor operating-systems scan        # extract slides, build the concept map
/tutor operating-systems story       # teaching handout + PDF
/tutor operating-systems teach paging
/tutor operating-systems quiz paging
/tutor operating-systems check       # review your own notes
/tutor operating-systems map
/tutor operating-systems exam-prep   # needs past papers in courses/<course>/
/tutor operating-systems cheatsheet

/full-learn operating-systems build  # the book-length version, with two review stops
/story-cards operating-systems all   # story cards, built on top of full-learn's output
```

`courses/` and `output/` are git-ignored, so course material and generated files stay out of the repo.

## Design principles

- **No out-of-syllabus content.** Only what appears in the slides is taught. Anything the model adds to make an explanation work has to be marked as supplementary.
- **Big picture first.** The course map comes before any single topic, and every `teach` answer starts by placing the topic in that map.
- **Explicit prerequisites.** Each concept records what it depends on, and the teaching order follows those dependencies, so no section relies on something explained later.
- **Every point traceable to a slide page.** Concepts and sections carry their source as lecture and physical page number (for example `L2 p19`), so a reader can check any claim against the original.

## Known limitations

An internal review in August 2026 compared generated material page by page against the slides it came from. What it found:

- **Paraphrase fidelity was high.** Of 40 sampled numbers and formulas, 31 matched the slides exactly.
- **Coverage had no gate.** What got covered depended on the model following the instruction to go through every page. In one sampled lecture, only about 25% of the pages were covered; large sections were dropped at the scan stage, and nothing downstream noticed.
- **Extraction is weak on maths and figures.** Formulas in the PDF text layer often come out garbled, so the model rebuilds them from its own knowledge instead of reading them from the slides. Code and diagrams that exist only as images are lost unless the page is flagged for a screenshot.
- **Fabrication slipped through.** The review found invented dates, quotes and numbers, and thresholds that had been changed from the slides' values. All the checks at the time were style checks, run by the same model that wrote the text.

After the review, several fixes were added. `scan` now has to write a page-to-concept coverage audit before `story` will run, figure-heavy pages are detected more reliably, and `full-learn`'s `verify_book.py` checks by script that every page of the material is assigned to a section or explicitly exempted. These checks still rely on source annotations that the model writes itself. Coverage has not been re-measured with an independent page-by-page sample since, so treat the generated material as a study aid to check against the slides, not a replacement for them.

## Showcase

[`examples/restaurant-story-act1.html`](examples/restaurant-story-act1.html) is a single self-contained HTML file you can open offline. It is the first act (3 episodes, 22 cards) of a five-act `story-cards` guide built for a graduate course on computer systems performance. The story world is a restaurant: slow service stands for latency, the kitchen manager for the OS kernel, the stoves for CPUs.

- The story is in Chinese. An English toggle may be added later.
- Each card cites the lecture slide pages it was built from. The slides themselves are not included.
- Exam-related annotations have been removed from this public excerpt.

## Repository layout

```
.claude/skills/
  tutor/          main skill: SKILL.md, references/ (per-command instructions), scripts/
  full-learn/     book pipeline: core/, modules/, templates/, scripts/
  story-cards/    story adaptation: SPEC.md, templates/, scripts/
  drill-paradigm/ per-exercise summaries
examples/         showcase excerpt (CC BY-NC 4.0)
```

## License

Code and skills: MIT, see [LICENSE](LICENSE). Showcase content in `examples/`: CC BY-NC 4.0, see [examples/LICENSE](examples/LICENSE).

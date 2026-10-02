# Discovery note

One page. Figures marked **(brief)** come from the Dhaga & Co. case-study brief. Anything marked **[TO COMPLETE]** is for the group to fill in. Do not replace a placeholder with a guess: if it is not known, say so.

Dhaga & Co. is a fictional company described in the brief. All data in this repository is invented stand-in data.

## Problem

Dhaga & Co. does not know which vendors and products are sending orders back for fit. The reason sits in a free-text "Other" box and in 410,000 reviews that nobody reads.

## Owner

Neha, Category Head. She uses the tool and approves every fix.

**[TO COMPLETE]** Confirm with Neha that she owns the outcome as well as the screen, and name who on her team clears the review queue each week.

## Evidence

| What | Figure | Source |
|---|---|---|
| Returns as a share of orders | 31% | (brief) |
| Returns whose reason is only "Other" free text | 44% | (brief) |
| Product reviews held, never analysed | 410,000, eighteen months deep | (brief) |
| Size charts | Differ by vendor | (brief) |
| What Neha says | "Most of the Other box is about fit, but I can only read a few hundred at a time." | (brief) |

**[TO COMPLETE]** Section references in the brief for each line above.

## Cost

| Line | Figure | Basis |
|---|---|---|
| "Other" returns a week | 6,547 | 48,000 orders x 31% x 44% (brief) |
| Cost of one return | **[TO COMPLETE]** | Not in the brief. Ask Faizan (Supply Chain). |
| Share of "Other" that is about fit | **[TO COMPLETE]** | Neha's view is "most". Fit Radar measures it. |
| Running Fit Radar each week | About $10 (about Rs 906) | Planning estimate in `docs/build_note.md`. Replace with the measured figure. |

## Success measure

- Reading accuracy: 85% or better agreement with 300 hand-labelled comments.
- Returns with no usable reason fall from 44% to under 10%.
- For approved fixes: the vendor's fit-return rate falls against similar vendors that were not changed, four weeks apart.

**[TO COMPLETE]** Neha's agreement to these targets.

## Ranked shortlist

| Rank | Option | Why this rank |
|---|---|---|
| 1 | Fit Radar: read return comments and reviews, flag vendor fit problems, suggest a size-chart fix | **[TO COMPLETE]** |
| 2 | Cash-on-delivery order check (MVP 2) | **[TO COMPLETE]** |
| 3 | **[TO COMPLETE]** | **[TO COMPLETE]** |

## Biggest assumption

That most "Other" return text is about fit, and that a vendor's fit problem shows up as a consistent direction (runs small, runs large, too short) that a size-chart change can fix.

How we will know: the share of fit in the first live run, and whether flagged vendors show one dominant direction. **[TO COMPLETE]** What we do if it is wrong.

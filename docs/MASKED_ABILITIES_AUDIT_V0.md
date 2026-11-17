# Audit: built or stored, but not yet doing work (observer, seed 2301)

Method: one full stock run of the controls pack (183 lessons, promotion every 20) with every
workspace assessment tallied, a search for fields that are written and never read, and
`run_observer_masked_abilities.py` for the two most promising.

## OBSERVED in the 183-lesson run
| what | finding |
|---|---|
| workspace, current evidence | offered 183, admitted 183 |
| workspace, resonance | offered 727, admitted 366 (exactly 2 per beat); 361 cut by `resonance_budget_cap` |
| workspace, learned recall (local association) | offered 6 times; it only fires for a bonded neighbour that is absent from the current experience |
| workspace, earned structures | offered 0 times though 4 P existed (none of their families was revisited after promotion) |
| workspace, contradiction | offered 3, admitted 3, mean score 0.67 |
| signals never above zero | `action_value`, `ethical_salience` (0.20 of the score weight between them) |
| `prediction_error` | constant 0.15 on current evidence; never computed from surprise |
| candidate quality | `perturbation_survival` and `compression_gain` are written as 0.0; `contradiction_tolerance` was 1.0 for every candidate |
| P `field_prototype_*` | computed for every candidate and every P, copied through promotion and refold, read by nothing |
| governance `t_g` | 0.5 throughout |

## Tested: the P field prototype as a recognition key (features only, 30 families, chance 3.3%)
unseen sentence naming all members -> right family first: 87%
naming only the first member: 33%; only the last member: 27%

## Tested: is novelty already measurable?
How far the best profile match stands above the crowd: 3.07 SD for sentences about taught
families, 2.26 SD for sentences about never-taught tokens; a midpoint cut separates 87%.
The groups overlap (lowest taught 1.76, highest never-taught 2.90).

One seed. "Not read" is from a text search of the engine packages and Workbench backend.

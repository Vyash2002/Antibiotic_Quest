> **SYNTHETIC DEMO DATA - these numbers are invented and must not be reported.**

# Antibiotic Quest - pilot results (2026-11-14)

## Primary hypothesis (knowledge score)

| measure | value |
|---|---|
| n participants (complete pre+post) | 40 |
| n excluded (incomplete) | 0 |
| pre-test mean (SD), out of 16 | 7.05 (3.86) |
| post-test mean (SD), out of 16 | 9.95 (3.95) |
| mean change (95% CI) | 2.90 (1.85 to 3.95) |
| median change (IQR) | 3.0 (1.0 to 5.0) |
| Shapiro-Wilk on differences (W, p) | 0.967, 0.2984 |
| paired t-test one-sided (t, df, p) | 5.605, 39, 9.15e-07 |
| paired t-test two-sided p | 1.83e-06 |
| Wilcoxon signed-rank one-sided (W+, p) | 632.5, 1.03e-05 |
| rank-biserial r (Wilcoxon effect size) | 0.799 |
| Cohen's dz (bootstrap 95% CI) | 0.89 (0.59 to 1.28) |
| class-average normalised gain <g> | 0.32 |
| primary test (by pre-registered rule) | paired t-test |
| primary p-value | 9.15e-07 |
| decision at alpha = 0.05 | reject H0 |
| KR-20 reliability of knowledge test (pre) | 0.81 |

**Primary test:** paired t-test (rule: paired t-test if Shapiro-Wilk p >= 0.05 on the differences). Report the effect size and CI, not only the p-value.

## Attitude / intention score (secondary, range 6-30, higher = more prudent)

Pre mean 17.8, post mean 20.9, Wilcoxon one-sided p = 4.58e-06 (n = 40).

## Topic-wise accuracy (exploratory, Holm-adjusted)

| topic | n_items | pre_accuracy_pct | post_accuracy_pct | p_wilcoxon | p_holm |
|---|---|---|---|---|---|
| Bacteria vs viruses | 4 | 43.1 | 68.1 | 0.0001 | 0.0002 |
| Antibiotic misuse | 5 | 49.5 | 63.5 | 0.0032 | 0.0088 |
| Infection prevention | 3 | 46.7 | 63.3 | 0.0039 | 0.0088 |
| AMR / superbugs | 4 | 36.2 | 53.8 | 0.0029 | 0.0088 |

## Items with the lowest pre-test accuracy

| item | statement | pre_correct_pct | post_correct_pct | p_holm |
|---|---|---|---|---|
| K08 | In India, a vertical red line on a medicine strip means it should be taken only with a doctor's prescription. | 12.5 | 25 | 1 |
| K13 | Antibiotic resistance occurs when your body becomes resistant to antibiotics and they no longer work as well. | 20 | 35 | 1 |
| K02 | Antibiotics are effective against colds and flu. | 32.5 | 65 | 0.0376 |
| K11 | Vaccines can reduce the need for antibiotics by preventing infections. | 35 | 65 | 0.1655 |
| K16 | Antibiotic-resistant infections could make medical procedures like surgery and cancer treatment much more dangerous. | 37.5 | 55 | 1 |

## Gameplay

Players: 40. Completed all 5 levels: 75%.

| level | players | median_time_sec | hints_per_player | accuracy_pct | completed_pct_of_starters |
|---|---|---|---|---|---|
| 1 | 40 | 72.5 | 0.8 | 51.5 | 100 |
| 2 | 37 | 69 | 0.8 | 46.5 | 92.5 |
| 3 | 34 | 67.5 | 0.9 | 51.8 | 85 |
| 4 | 32 | 69 | 0.8 | 46.2 | 80 |
| 5 | 30 | 103.5 | 1 | 47.5 | 75 |

### Hardest in-game questions

| question_id | error_rate | most_chosen_wrong_option | wrong_option_text |
|---|---|---|---|
| AQ037 | 78.9 | B | Regular handwashing |
| AQ026 | 76.9 | A | Buy the same antibiotic again |
| AQ024 | 76.2 | A | Switch to her brother's antibiotics |
| AQ012 | 76.2 | B | False |
| AQ056 | 73.3 | B | It has no time frame |

### Engagement vs learning (Spearman, exploratory)

| engagement_measure | outcome | spearman_rho | p | n | p_holm |
|---|---|---|---|---|---|
| levels_completed | post_knowledge | 0.342 | 0.0306 | 40 | 0.2144 |
| levels_completed | knowledge_change | 0.021 | 0.8973 | 40 | 1 |
| game_accuracy | post_knowledge | 0.678 | 0 | 40 | 0 |
| game_accuracy | knowledge_change | 0.044 | 0.7888 | 40 | 1 |
| total_time_sec | post_knowledge | 0.075 | 0.6476 | 40 | 1 |
| total_time_sec | knowledge_change | 0.075 | 0.647 | 40 | 1 |
| points | post_knowledge | 0.703 | 0 | 40 | 0 |
| points | knowledge_change | 0.037 | 0.8188 | 40 | 1 |
| hints | post_knowledge | 0.45 | 0.0036 | 40 | 0.0289 |
| hints | knowledge_change | 0.243 | 0.1303 | 40 | 0.7819 |

## Sample size reference (paired t-test, alpha 0.05, power 0.80)

| cohens_dz | n_one_sided_t | n_two_sided_t | n_one_sided_wilcoxon_approx | power_with_n30_one_sided | power_with_n40_one_sided |
|---|---|---|---|---|---|
| 0.3 | 71 | 90 | 75 | 0.484 | 0.587 |
| 0.4 | 41 | 52 | 43 | 0.69 | 0.8 |
| 0.5 | 27 | 34 | 29 | 0.848 | 0.928 |
| 0.6 | 19 | 24 | 20 | 0.941 | 0.981 |
| 0.8 | 12 | 15 | 13 | 0.996 | 1 |
| 1 | 8 | 10 | 9 | 1 | 1 |

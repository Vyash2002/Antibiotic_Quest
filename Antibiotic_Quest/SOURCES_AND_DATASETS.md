# External datasets and sources for Antibiotic Quest

The game needs no clinical ML dataset. The real datasets below serve three purposes:
(1) **validated questionnaire items** for the pre/post test, (2) **baseline numbers** to
compare your pilot against, and (3) **burden figures** for the Background slide.

## A. Survey instruments and population baselines (most useful)

| Source | What you get | Use in the project | Link |
|---|---|---|---|
| WHO (2015) *Antibiotic resistance: multi-country public awareness survey* | 14-question public questionnaire (Annex) with answer key; ~10,000 respondents in 12 countries incl. **India (n = 1,023)** | Items K02, K05, K06, K12, K13, K14 and K16 are adapted from it. Compare your pre-test with India's 2015 results (e.g. 75% of Indian respondents wrongly said colds/flu can be treated with antibiotics) | https://medbox.org/document/antibiotic-resistance-multi-country-public-awareness-survey |
| Eurobarometer 97.1 (ZA7886, Feb-Mar 2022), AMR module "QC" via GESIS | **Microdata** (respondent-level) for the 2022 Special Eurobarometer 522 on AMR; free download after registration | Source of the classic knowledge items (K01, K02, K07, K15). Lets you show how a large population answered the same items | https://www.gesis.org/en/eurobarometer-data-service/data-and-documentation/standard-special-eb/study-overview/eurobarometer-971-za7886-february-march-2022 |
| WHO Europe KAB survey (Frontiers in Public Health, 2023) | Same Eurobarometer questionnaire used in 14 non-EU countries | Evidence that the items are re-used and validated outside the EU | https://www.frontiersin.org/articles/10.3389/fpubh.2023.1274818/full |

## B. Burden and resistance data (Background slide)

| Source | What you get | Link |
|---|---|---|
| IHME GHDx - GBD 2021 Bacterial AMR Burden Estimates 1990-2021 and Forecasts 2022-2050 | Downloadable estimates by country, incl. India (deaths attributable to / associated with AMR) | https://ghdx.healthdata.org/record/ihme-data/gbd-2021-bacterial-amr-estimates-forecasts-1990-2050 |
| GRAM study, *The Lancet* (Sep 2024) | 1.14 M attributable / 4.71 M associated deaths in 2021; >39 M attributable deaths forecast 2025-2050, South Asia highest | https://www.ox.ac.uk/news/2024-09-17-antibiotic-resistance-has-claimed-least-one-million-lives-each-year-1990 |
| WHO GLASS report 2025 + dashboard | 1 in 6 lab-confirmed infections resistant (2023); ~1 in 3 in South-East Asia Region | https://www.who.int/news/item/13-10-2025-who-warns-of-widespread-resistance-to-common-antibiotics-worldwide |
| ICMR AMRSN Annual Report 2024 | ~99,000 culture-positive isolates from Indian hospitals, resistance trends | https://www.icmr.gov.in/icmrobject/uploads/Report/1763981012_icmramrsnannualreport2024.pdf |
| NCDC (MoHFW) NARS-Net reports | National AMR surveillance reports 2017 onwards | https://ncdc.mohfw.gov.in/reports/ |
| India NAP-AMR 2.0 (2025-2029) | Policy context; launched 18 Nov 2025 during WAAW | https://www.downtoearth.org.in/health/waaw-2025-indias-much-awaited-second-version-of-the-national-action-plan-on-amr-released |
| WHO World AMR Awareness Week 2026 (18-24 Nov) | Theme "One Health, one action: Prevent AMR now" | https://www.who.int/campaigns/world-amr-awareness-week/world-amr-awareness-week-2026 |

## C. Content sources for questions (already used in `AMR_Facts.csv`)

- WHO antibiotic resistance and AMR fact sheets
- CDC "Antibiotic Do's and Don'ts", "Antibiotics aren't always the answer", handwashing pages
- MoHFW "Medicines with the Red Line" campaign (J Family Med Prim Care 2022, doi:10.4103/jfmpc.jfmpc_1811_21)
- e-Bug (UKHSA): free school resources on microbes, hygiene and antibiotics, incl. evaluated games - https://www.e-bug.eu

## D. Related work (gamified AMR education with pre/post tests)

| Study | Design | Link |
|---|---|---|
| Gamified KAP intervention for school children, Mysuru (Frontiers in Public Health, 2025) | Same questionnaire pre and post; Indian setting | https://www.frontiersin.org/journals/public-health/articles/10.3389/fpubh.2025.1574647/abstract |
| Gamified intervention for healthcare professionals/students on rational antimicrobial use, Mysuru (2025) | 50 participants, pre/post, based on ICMR 2022 guidelines | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12597959/ |
| e-Bug antibiotic games evaluation (2017) | Matched pre/post questionnaires, McNemar test per item | https://pmc.ncbi.nlm.nih.gov/articles/PMC5384992 |
| Antibiotic card game vs lecture, medical students (RDME 2025) | Randomised, 100 students, pre/post | https://rdme.tbzmed.ac.ir/FullHtml/rdme-33309 |

## Not needed unless you add speech input

- Project Vaani / RESPIN (Kannada speech) from the ASHA Dhwani guide: speech-recognition data only.
- Clinical antimicrobial-susceptibility datasets (e.g. on Kaggle): these are for prediction models, not an awareness game.

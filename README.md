# Student-Rank (Anti-Slytherin) 🎓

**A Fairness-Centered Algorithm Suite for Preference-Based Group Assignment**

*Version: Current (backwards compatible with all prior command usage)*

---

## The Problem This Solves

Every semester, instructors running project-based courses face the same uncomfortable moment: students form teams, and someone ends up somewhere they did not want to be. In Harry Potter terms, they end up in Slytherin. Proximity bias, social dynamics, and the randomness of who speaks first all conspire against fairness. The student who ranked five startup ideas and got none of them has no recourse. The instructor has no visibility into how badly the outcome diverged from what was possible.

Anti-Slytherin starts from a different premise: collect explicit ranked preferences first, then let an algorithm do the assignment. The goal is not simply to maximize average satisfaction, which can hide individual failures behind aggregate statistics. The goal is to ensure that no student receives a rank-6 (unranked) assignment if the preference data made a better outcome structurally possible.

This turns out to be a harder problem than it looks. Naive popularity-based company selection creates preference distributions that are structurally unresolvable for some students before placement even begins. The research documented here is the systematic investigation of that failure mode and the construction of algorithms that address it layer by layer.

---

## The Research Arc

The system began as a simple ranker: collect Google Form data, run one of three placement algorithms, output group assignments. That original capability is fully preserved.

Before simulation work began, the pre-criticality algorithms were used to successfully place three groups of real students at NJIT. Only one swap was needed across all three placements. This early real-world success is an important data point: it suggests that at least in the NJIT context, student selection of student-proposed companies may be highly clumped in ways that are favorable to placement algorithms. Real-world preference data may be meaningfully non-normal compared to synthetic data, and in a direction that helps rather than hurts. This hypothesis has not yet been formally tested but informs how the simulation results should be interpreted.

Monte Carlo simulation then revealed a structural problem: under popularity-based company selection, it was only statistically possible for every student to land in a top-five choice approximately one third of the time. This was a major turning point. No placement algorithm, however clever, can fix a structurally non-viable configuration — if a student has no ranked option among the selected companies before placement begins, a rank-6 assignment is inevitable.

The solution was a new Phase 1 strategy called **criticality**. Rather than selecting companies by how popular they are, criticality evaluates each candidate company by asking: if this company were removed, how many student assignments would become structurally impossible? Companies whose removal causes the most damage are selected first, and the process iterates until the pool is filled. Ties are resolved by secondary ordering. Criticality raised structural viability from approximately 34% of trials to effectively 100%.

With criticality in place, the next question was how well the placement algorithms could achieve Perfect Top-5 outcomes — trials where every student received a rank 1-5 assignment with no rank-6 fallbacks. Under criticality selection the results were: Fill First 2.8%, Best First 0.7%, Fragility Mirror 0.6%, Rank First 0.4%. For comparison, under popularity-based selection those rates were Fill First 2.1%, Best First 1.0%, and Rank First 0.7% — but applied only to the 34% of trials that were structurally viable. Criticality roughly tripled the absolute Perfect Top-5 rates by ensuring every trial starts from a sound configuration. Even so, Fill First's 2.8% was far from the 100% target.

The success of criticality raised a natural question: could a mirror of criticality applied at the placement stage similarly improve outcomes? This motivated the **Fragility Mirror** algorithm, which at each step identifies the most structurally vulnerable student (fewest viable options remaining) and places them first, choosing the assignment that minimizes cascading damage to other students. Fragility Mirror is philosophically sound but has a known weakness in its endgame: as the final few students are placed, the fragility landscape becomes sparse and the scoring criteria degrade, producing worse performance than the simpler algorithms in those final steps. A better endgame strategy remains a possibility for future improvement, though the working hypothesis is that rank-improvement swapping in the planned Stage 2 pipeline will absorb most of these cases without requiring targeted fixes.

The focus then shifted to a different question: rather than trying to get any single algorithm to achieve Perfect Top-5 directly, could the data be conditioned so that swapping becomes feasible? For 30 students assigned to 10 companies, there are approximately 5.6 × 10¹⁸ possible assignments from the start — swapping the full space is not tractable. But if an algorithm can get close enough to a perfect solution, most repairs require swap chains of length three or fewer, giving approximately 15³ = 3,375 options to evaluate. The goal became: get every trial to a configuration where no more than three swaps are needed.

Prior analysis had shown that Fill First works best with clumped data. The concept behind **Dual Outlier Matching (DOM)** was to create that clumping artificially. DOM identifies outlier companies — those that almost no student ranked — and pairs them with outlier students — those with almost no viable options elsewhere. Those companies are filled completely first. The remaining students, now more clumped in their preferences, are passed to the normal Phase 1 and Phase 2 pipeline.

Testing DOM combined with Fill First and criticality selection across 1,000 trials for N=30 students placed into between 8 and 12 companies shows that the swappability threshold of fewer than 3 swaps needed is achievable. The sweet spot is when DOM fills the first three to four companies before handing off to the main pipeline. To date, testing has only been conducted at N=30, and swapping itself has not yet been implemented.

---

## Overview

Student-Rank (informally called Anti-Slytherin) is a Python-based system for optimally assigning students to startup company groups based on ranked preferences. It implements four placement algorithms, two company-selection strategies, an optional Dual Outlier Matching pre-processing phase, and a Monte Carlo simulation harness for statistical comparison across many trials.

All original command-line arguments remain intact. New flags are additive and default to backward-compatible behavior.

---

## Quick Start

### For Technical Users

```bash
# Install dependencies
pip install -r requirements.txt

# Run all four algorithms with criticality selection, 100 trials
python ranker2.py --trials 100 --students 50 --total_companies 20 --selected_companies 10 \
    --selection criticality --algorithms 0 1 2 3

# Original usage (fully backwards compatible)
python ranker2.py --trials 100 --students 50 --total_companies 20 --selected_companies 10

# Generate standalone executable
pyinstaller --onefile --name StudentRanker ranker2.py
```

### For Non-Technical Users

```bash
# Pre-built executable — all arguments identical
StudentRanker.exe --trials 50 --students 30 --total_companies 16 --selected_companies 8
```

---

## Requirements

```bash
pip install -r requirements.txt
```

**Core dependencies:**
- `pandas >= 2.2.3` — data manipulation and analysis
- `numpy >= 2.2.1` — numerical computing
- `Faker >= 33.1.0` — synthetic company and student name generation
- `tqdm >= 4.66.0` — progress bars (optional, enhances UX)

**Development dependency:**
- `PyInstaller >= 6.15.0` — standalone executable creation

---

## System Architecture

The pipeline has evolved from a two-phase system to a four-phase system. Phases -1 and 1 govern which companies receive students; Phase 2 governs how students are placed.

### Phase -1: Dual Outlier Matching (DOM) *(optional)*

When enabled via `--dom`, DOM runs before company selection. It identifies outlier companies (few students ranked them) and pairs them with outlier students (few viable ranked options). Those companies are filled completely first, then the remaining companies and students proceed to normal Phase 1 and Phase 2 processing.

The `--dom N` parameter specifies how many companies should remain when DOM stops processing. Companies locked by DOM = `selected_companies` minus N. DOM = 0 (the default) disables this phase entirely.

**Research finding:** moderate DOM (locking 2–3 companies) improves average rank and stability. Aggressive DOM (locking 7–8 companies) maximizes Perfect Top-5 rates but increases volatility.

### Phase 1: Company Selection

Selects which companies from the full pool will receive student assignments. Two strategies are available via `--selection`:

- **`ranked` (default)** — Weighted popularity scoring. Rank weights [5,4,3,2,1] for ranks 1–5. Composite score = 75% rank score + 25% adjusted score. Ties broken by rank-1 count, rank-2 count, etc. This is the original method; all prior results used this.
- **`criticality`** — For each candidate company, computes how many student assignments become structurally impossible if that company is removed. Companies whose removal causes the most damage are selected first. Research finding: criticality dramatically improves structural viability compared to ranked selection.

### Phase 2: Placement Algorithms

Four algorithms assign students to the selected companies. All four share the same input and output format and are fully interchangeable.

#### Algorithm 0: Fill First *(get_student_groups)*

Company-centric. Processes companies in reverse ranking order (best companies last). Fills each company completely before moving to the next. Proposed-company students get automatic selection; remaining slots filled by rank then remaining-rank-average tie-break.

Fill First is the primary subject of ongoing research. Although it produces a slightly higher average student rank than Rank First, it is currently the only algorithm that consistently achieves the structural condition required for swappability: configurations where all remaining rank dissatisfaction can be repaired in fewer than three swap chains.

#### Algorithm 1: Rank First *(get_rank_first_student_groups)*

Student preference-centric. Processes all rank-1 preferences across all companies simultaneously, then rank-2, etc. Maximizes top-preference fulfillment. Historically produces the highest student satisfaction rates but the lowest Perfect Top-5 rate.

#### Algorithm 2: Best First *(get_best_first_student_groups)*

Iterative quality optimization. Each round, every company selects its single best available student. Continues until all positions are filled. Balances quality with fairness but produces more variable results.

#### Algorithm 3: Fragility Mirror *(get_fragility_mirror_student_groups)*

Structurally defensive placement. At each step:

1. Computes fragility for all unplaced students. Fragility = number of remaining viable companies for that student (only ranks 1–5 count as viable; rank 6 is a fallback, not a viable option).
2. Selects the most fragile student (lowest viable options remaining).
3. For each candidate company, simulates the placement and scores by: (a) backup fragility increase caused for other students, (b) total fragility shift across all students, (c) the student's numerical rank for that company as a final tie-break.
4. Places the student in the company that minimizes cascading damage.
5. Recomputes fragility dynamically after every placement.
6. If no viable ranked choice exists for a student, assigns the lowest numerical rank available (rank-6 fill).

Fragility Mirror has a known weakness in its endgame: as the final few students are placed, the fragility landscape becomes sparse and scoring criteria degrade. A better endgame strategy remains a possibility, though the working hypothesis is that rank-improvement swapping in Stage 2 of the planned swap pipeline will absorb most of these cases.

---

## Structural Viability

A trial is **structurally viable** if every student has at least one selected company ranked 1–5 in their preferences. If any student has zero viable options among the selected companies, the trial is structurally non-viable — Slytherin is structurally possible regardless of algorithm behavior.

The function `check_structural_viability()` evaluates this before placement runs. The result is stored in the `structurally_viable` column of the output CSV and reported as **Structural Viability Rate** in the terminal summary.

---

## Complete Usage Guide

### Trial Mode (Primary Use Case)

Generates synthetic preference data and runs Monte Carlo statistical comparisons across multiple trials.

#### Core Arguments

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--trials` | int | 1 | Number of trials to run |
| `--students` | int | 30 | Number of students per trial |
| `--total_companies` | int | 20 | Total companies available for ranking before selection |
| `--selected_companies` | int | 10 | Number of companies selected for assignment |
| `--selection` | str | ranked | Company selection method: `ranked` or `criticality` |
| `--dom` | int | 0 | Dual Outlier Matching threshold; 0 = disabled. Stop DOM when this many selected companies remain (companies locked = selected_companies − dom) |
| `--algorithms` | int+ | [0] | Algorithms to run: 0=Fill First, 1=Rank First, 2=Best First, 3=Fragility Mirror. Multiple allowed: `--algorithms 0 1 2 3` |
| `--output_file` | str | algorithm_statistics.csv | Output CSV filename |
| `--save_input_data` | flag | off | Also save per-trial input statistics to a second CSV |
| `--seed` | int | time-based | Random seed for reproducible results |

#### Advanced Arguments

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--suppress_terminal_output` | flag | off | Minimize console output during trials |
| `--no_progress_bar` | flag | off | Disable tqdm progress bar |
| `--progress_interval` | int | 10 | Show progress every N trials |

#### Example Commands

**Standard comparison, all four algorithms, criticality selection:**
```bash
python ranker2.py --trials 100 --students 50 --total_companies 20 --selected_companies 10 \
    --selection criticality --algorithms 0 1 2 3
```

**DOM analysis (lock 7 companies, Fill First only):**
```bash
python ranker2.py --trials 1000 --students 30 --total_companies 30 --selected_companies 10 \
    --selection criticality --algorithms 0 --dom 3 --seed 42 --output_file dom_analysis.csv
```

**Fill First only with criticality (current recommended baseline):**
```bash
python ranker2.py --trials 100 --students 30 --total_companies 20 --selected_companies 10 \
    --selection criticality
```

**Original behavior (fully backwards compatible):**
```bash
python ranker2.py --trials 100 --students 50 --total_companies 20 --selected_companies 10
```

**High-competition scenario:**
```bash
python ranker2.py --trials 200 --students 30 --total_companies 40 --selected_companies 10 \
    --selection criticality --algorithms 0 1 2 3
```

**Seeded reproducible run:**
```bash
python ranker2.py --trials 500 --algorithms 0 3 --seed 42 --output_file ff_vs_fragility.csv
```

### Legacy Mode (Single File Processing)

For processing an existing CSV file with real student preference data collected via Google Forms or similar.

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--file` | str | required | Path to input CSV file |
| `--type` | int | required | Algorithm: 0=Fill First, 1=Rank First, 2=Best First |
| `--students` | int | all | Number of students to process |
| `--suppress_terminal_output` | flag | off | Minimize output |

```bash
python ranker2.py --file data/form_test_data_cc.csv --type 1 --students 30
```

---

## Company Selection Architecture

### Stage 1: Pool Generation

`--total_companies` defines the full universe of companies. All companies receive student preference rankings. Larger pools create more realistic preference distributions and competitive pressure.

### Stage 2: Selection

`--selected_companies` determines how many top companies receive student assignments. `--selection` controls which companies are chosen.

**Selection rate examples:**
- High competition (20% selection): `--total_companies 50 --selected_companies 10`
- Balanced competition (50% selection): `--total_companies 20 --selected_companies 10`
- Low competition (80% selection): `--total_companies 15 --selected_companies 12`

---

## Output Specifications

### Trial Mode Output *(algorithm_statistics.csv)*

Each row represents one trial. The first two columns are trial-level; remaining columns repeat per algorithm using the prefix shown below.

#### Column Prefixes

| Prefix | Algorithm |
|--------|-----------|
| `fill_first_` | Algorithm 0 — Fill First |
| `rank_first_` | Algorithm 1 — Rank First |
| `best_first_` | Algorithm 2 — Best First |
| `fragility_mirror_` | Algorithm 3 — Fragility Mirror |

#### Trial-Level Columns

| Column | Description |
|--------|-------------|
| `trial` | Trial number (1-indexed) |
| `structurally_viable` | True if every student had at least one company ranked 1–5 among the selected companies |

#### Per-Algorithm Columns *(repeated for each prefix)*

| Column | Description |
|--------|-------------|
| `{prefix}_avg_student_ranking` | Mean rank assigned across all students (lower = better) |
| `{prefix}_std_student_ranking` | Standard deviation of assigned ranks |
| `{prefix}_median_student_ranking` | Median assigned rank |
| `{prefix}_iqr_student_ranking` | Interquartile range (Q3 minus Q1) |
| `{prefix}_student_satisfaction_percent` | Percentage of students assigned ranks 1–3 |
| `{prefix}_student_satisfaction_top4_percent` | Percentage assigned ranks 1–4 |
| `{prefix}_student_satisfaction_top5_percent` | Percentage assigned ranks 1–5 |
| `{prefix}_students_got_choice_N_count` | Raw count of students assigned rank N (N = 1–6) |
| `{prefix}_students_got_choice_N_percent` | Percentage of students assigned rank N |

#### Terminal Summary Metrics

After all trials complete, the terminal prints per-algorithm:
- Average Student Ranking ± std
- Student Satisfaction Top-3, Top-4, Top-5 with confidence ranges
- Perfect Top-5 Rate (All Trials) — percentage of trials where zero students received rank 6
- Perfect Top-5 Rate (Structurally Viable Only) — same metric, restricted to structurally viable trials
- Structural Viability Rate — percentage of trials where every student had at least one viable option

### Input Data Summary *(optional)*

Generated when `--save_input_data` is passed. Saved to `{output_file}_input_summary.csv`.

| Column | Description |
|--------|-------------|
| `trial` | Trial number |
| `total_students` | Number of students in the trial |
| `total_companies` | Total companies in the ranking pool |
| `companies_ranked` | Number of companies that received at least one ranking |
| `avg_company_ranking` | Average ranking across all companies |
| `company_popularity_std` | Standard deviation of company popularity |
| `company_ranking_skewness` | Asymmetry of the company ranking distribution |
| `company_ranking_kurtosis` | Tail heaviness of the company ranking distribution |
| `company_entropy` | Diversity measure of company popularity |
| `company_outlier_count` | Total companies with unusual ranking patterns |
| `company_outlier_percentage` | Percentage of companies that are outliers |
| `highly_ranked_outlier_count` | Extremely popular companies (below Q1 − 1.5×IQR) |
| `highly_ranked_outlier_percentage` | Percentage of extremely popular companies |
| `lowly_ranked_outlier_count` | Extremely unpopular companies (above Q3 + 1.5×IQR) |
| `lowly_ranked_outlier_percentage` | Percentage of extremely unpopular companies |
| `best_company_avg_ranking` | Average ranking of the highest-ranked company |
| `worst_company_avg_ranking` | Average ranking of the lowest-ranked company |
| `company_ranking_range` | Range between best and worst company average rankings |
| `top_company` | Name of the highest-scored company |
| `top_company_score` | Composite score of the top company |
| `second_company` | Name of the second-ranked company |
| `second_company_score` | Composite score of the second company |
| `third_company` | Name of the third-ranked company |
| `third_company_score` | Composite score of the third company |
| `most_included_company` | Company appearing in the most student top-5 rankings |
| `most_included_count` | Number of students who included that company |
| `company_score_range` | Range between highest and lowest composite company scores |
| `total_rankings_given` | Total ranked preferences submitted (students × 5) |
| `total_unranked_assignments` | Total rank-6 assignments across all students |

### Legacy Mode Output

Student group assignments saved to `ranker2data_{algorithm}.csv`. Format: one row per company, columns for each assigned student and their rank.

---

## Algorithm Performance

### Typical Characteristics

Based on 1,000-trial Monte Carlo runs under criticality selection. Exact values vary with student count, company count, and selection strategy.

- **Fill First:** Student satisfaction 85–95%. Average ranking 1.8–2.2. Reliable and predictable. The only algorithm currently achieving the swappability threshold. Primary research subject.
- **Rank First:** Student satisfaction 88–96%. Average ranking 1.7–2.0. Maximizes preference fulfillment but lowest Perfect Top-5 rate (0.4%).
- **Best First:** Student satisfaction 70–85%. Average ranking 2.2–2.8. More variable. Perfect Top-5 rate 0.7%.
- **Fragility Mirror:** Designed to minimize structural collapse. Perfect Top-5 rate 0.6%. Known endgame weakness.

### Perfect Top-5 Rates by Selection Method

| Algorithm | Ranked Selection (of 34% viable) | Criticality Selection (100% viable) |
|-----------|----------------------------------|--------------------------------------|
| Fill First | 2.1% | 2.8% |
| Best First | 1.0% | 0.7% |
| Rank First | 0.7% | 0.4% |
| Fragility Mirror | not tested | 0.6% |

### DOM Performance Profile *(1,000 trials, Fill First, Criticality, 30 students / 10 companies)*

> **Note:** DOM parameter N = companies remaining after DOM phase. Companies locked = 10 − N.

- **DOM 7–9 (light, 1–3 companies locked):** Best average rank. Stable Top-3 and Top-4 satisfaction. Modest Perfect Top-5 improvement.
- **DOM 4–6 (moderate, 4–6 companies locked):** Good balance of average rank and Top-5 gains. Recommended starting point.
- **DOM 1–3 (aggressive, 7–9 companies locked):** Perfect Top-5 rate spikes sharply (up to ~54% at DOM 1). Average rank degrades.

DOM does not meaningfully increase trial-to-trial volatility (standard deviation stays within ~1–1.4 students across all DOM levels).

---

## File Structure

```
Student-Rank/
├── ranker2.py                  # Main program — all algorithms, selection, DOM, simulation
├── cparser.py                  # CSV parsing utilities for legacy mode
├── requirements.txt            # Python dependencies
├── StudentRanker.exe           # Standalone executable (generated via PyInstaller)
├── data/
│   ├── form_test_data*.csv     # Sample Google Form preference data files
│   ├── rank_data.json          # JSON format test data
│   └── rank_your_sheet.csv     # Template for manual data entry
├── results/
│   ├── *_first_*.csv           # Algorithm-specific result files
│   ├── criticality_dom*.csv    # DOM sweep analysis output files
│   └── bf_bu_results.jpg       # Performance visualization
└── utilities/
    ├── form_data_generator.py  # Synthetic data generation
    ├── analyze_data.py         # Data analysis utilities
    ├── companies.txt           # Company name database
    └── names_and_emails.txt    # Student identity database
```

---

## Input File Format (Legacy Mode)

The system expects a specific CSV structure from Google Forms or equivalent:

- **Header Row:** required
- **Core Columns:** Timestamp, Email, Name (first three columns)
- **Company Columns:** format `"CompanyName - ProposerEmail@example.com"`
- **Ranking Values:** integers 1–5 (student preferences)
- **Missing Rankings:** empty cells treated as rank 6 (unranked)

```
Timestamp,Email,Name,TechCorp - john@example.com,DataSys - jane@example.com
2024-01-01,student1@school.edu,Alice Johnson,1,3
2024-01-01,student2@school.edu,Bob Smith,2,1
```

---

## Technical Implementation

### Data Generation

For each student: select 5 random companies from the pool, assign unique ranks 1–5, set all other companies to rank 6. Ensures no duplicate rankings per student.

### Criticality Scoring

For each candidate company: simulate removal, count how many students would lose all viable options. Companies are selected in order of decreasing removal-damage. Ties resolved by secondary criteria; process iterates until pool is filled.

### Fragility Computation

Fragility(s) = count of selected companies where student s has rank 1–5. Rank 6 is strictly a fallback and does not count as a viable option. Recomputed after every placement.

Cascading (induced) fragility: placing student s in company c decreases the fragility of each other student who also had c as a viable option. The algorithm scores each candidate placement by the number of students whose fragility decreases as a result.

### Performance

- Vectorized operations via Pandas and NumPy
- 3.5× speedup on small datasets (30 students, 10 companies)
- 9.7× speedup on large datasets (100+ students, 20+ companies)

### Adding a Custom Algorithm

```python
def your_algorithm(df: pd.DataFrame, ttdf: pd.DataFrame,
                   num_students: int, suppress_output: bool,
                   proposed_companies: dict) -> pd.DataFrame:
    # Your implementation
    return student_groups_df

# Register in algorithm_functions dict:
algorithm_functions = {
    0: ('Fill First', get_student_groups),
    1: ('Rank First', get_rank_first_student_groups),
    2: ('Best First', get_best_first_student_groups),
    3: ('Fragility Mirror', get_fragility_mirror_student_groups),
    4: ('Custom', your_algorithm)  # add here
}
```

Then update the `--algorithms` choices and prefix lookup lists in the argument parser and summary sections.

---

## Research Context

This system was developed and presented at USASBE (United States Association for Small Business and Entrepreneurship) as *Anti-Slytherin: A Fairness-Centered Approach to Team Formation* by Mark Annett, Professor of Practice, NJIT Martin Tuchman School of Management.

### Planned Future Work

- **Anti-Slytherin Swaps (Stage 1):** post-assignment repair that eliminates any remaining rank-6 assignments via swap chains of length ≤ 3. Fill First under criticality selection is currently the only algorithm that statistically reaches the condition where fewer than 3 swap chains are needed. This is the next implementation target.
- **Rank-Improvement Swaps (Stage 2):** a second swap pass that moves students toward higher preferences without creating new rank-6 assignments. Expected to absorb most remaining satisfaction gaps, including Fragility Mirror endgame cases.
- **Fragility Mirror endgame:** known weakness in late-stage placement. Targeted repair may be unnecessary if Stage 2 swapping resolves the same cases.
- **Scale analysis:** understand full algorithm behavior outside the N=30 baseline.
- **Accessibility:** make the tool more accessible to non-technical instructors.

---

## Support and Bug Reports

When reporting issues, please include:
- Full command-line arguments used
- Complete error message or traceback
- Operating system and Python version (`python --version`)
- Sample data if applicable

---

*This documentation reflects the current state of the Student-Rank / Anti-Slytherin system. For the latest updates, see the repository commits.*

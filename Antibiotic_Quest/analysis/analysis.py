"""Antibiotic Quest - pilot analysis (Datasets 2 and 3 of the project plan).

Usage (from the package folder):
    python analysis/analysis.py \
        --prepost data/Pre_Post_Test_Results.csv \
        --log data/Gameplay_Answer_Log.csv \
        --levels data/Gameplay_Analytics.csv \
        --out results

    # dry run on synthetic data (charts get a "SYNTHETIC" banner):
    python analysis/analysis.py --prepost data/synthetic/SYNTHETIC_Pre_Post_Test_Results.csv \
        --log data/synthetic/SYNTHETIC_Gameplay_Answer_Log.csv \
        --levels data/synthetic/SYNTHETIC_Gameplay_Analytics.csv --out results_synthetic

    # sample-size table only:
    python analysis/analysis.py --power-only

Pre-registered analysis plan (fix this BEFORE you look at real data):
  H0: mu_post = mu_pre,  H1: mu_post > mu_pre  (one-sided, alpha = 0.05) on the 16-item knowledge score.
  Primary test: paired t-test if the paired differences pass Shapiro-Wilk (p >= 0.05),
  otherwise the Wilcoxon signed-rank test. Effect size: Cohen's dz with a bootstrap 95% CI.
  Everything else (topics, items, attitude, engagement) is secondary/exploratory and Holm-adjusted.
Requires: pandas, numpy, scipy, matplotlib.
"""
import argparse, os, textwrap
from datetime import date

import numpy as np
import pandas as pd
from scipy import stats

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALPHA = 0.05
TOPIC_LABELS = {"T1_bacteria_vs_viruses": "Bacteria vs viruses", "T2_antibiotic_misuse": "Antibiotic misuse",
                "T3_infection_prevention": "Infection prevention", "T4_amr": "AMR / superbugs",
                "T5_mixed_champion": "Final level (mixed)"}

# ---- chart styling (reference palette from the dataviz method; validated light-mode slots 1-2)
PRE_C, POST_C, SINGLE_C = "#2a78d6", "#eb6834", "#2a78d6"
SURFACE, INK, INK2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"


# ============================================================ helpers
def holm(pvals):
    p = np.asarray(pvals, float)
    order = np.argsort(p)
    adj = np.empty_like(p)
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, (len(p) - rank) * p[i])
        adj[i] = min(1.0, running)
    return adj


def md(df):
    """DataFrame -> GitHub markdown table (no extra dependency)."""
    cols = [str(c) for c in df.columns]
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    def fmt(v):
        if v is None or (isinstance(v, float) and np.isnan(v)):
            return ""
        if isinstance(v, (float, np.floating)):
            return f"{v:.4g}"
        return str(v)
    for r in df.astype(object).itertuples(index=False):
        out.append("| " + " | ".join(fmt(v) for v in r) + " |")
    return "\n".join(out)


def kr20(items01):
    """Kuder-Richardson 20 reliability for 0/1 items (participants x items)."""
    x = np.asarray(items01, float)
    k = x.shape[1]
    p = x.mean(axis=0)
    var_total = x.sum(axis=1).var(ddof=1)
    return np.nan if var_total == 0 else (k / (k - 1)) * (1 - (p * (1 - p)).sum() / var_total)


def paired_power(dz, n, alpha=ALPHA, one_sided=True):
    df = n - 1
    tcrit = stats.t.ppf(1 - alpha if one_sided else 1 - alpha / 2, df)
    nc = dz * np.sqrt(n)
    return 1 - stats.nct.cdf(tcrit, df, nc) + (0 if one_sided else stats.nct.cdf(-tcrit, df, nc))


def n_for_power(dz, power=0.8, alpha=ALPHA, one_sided=True):
    for n in range(3, 2000):
        if paired_power(dz, n, alpha, one_sided) >= power:
            return n
    return np.nan


def power_table():
    rows = []
    for dz in (0.3, 0.4, 0.5, 0.6, 0.8, 1.0):
        n1, n2 = n_for_power(dz), n_for_power(dz, one_sided=False)
        rows.append(dict(cohens_dz=dz, n_one_sided_t=n1, n_two_sided_t=n2,
                         n_one_sided_wilcoxon_approx=int(np.ceil(n1 / 0.955)),
                         power_with_n30_one_sided=round(paired_power(dz, 30), 3),
                         power_with_n40_one_sided=round(paired_power(dz, 40), 3)))
    return pd.DataFrame(rows)


def style_axes(ax, title=None, xlabel=None, ylabel=None):
    ax.set_facecolor(SURFACE)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(AXIS)
    ax.tick_params(colors=INK2, labelsize=9)
    ax.yaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    if title:
        ax.figure._aq_title = title
    if xlabel:
        ax.set_xlabel(xlabel, color=INK2, fontsize=10)
    if ylabel:
        ax.set_ylabel(ylabel, color=INK2, fontsize=10)


def finish(fig, path, synthetic, footer):
    if synthetic:
        fig.text(0.5, 0.995, "SYNTHETIC DEMO DATA - NOT STUDY RESULTS", ha="center", va="top",
                 color="#d03b3b", fontsize=9, fontweight="bold")
    fig.text(0.01, 0.01, footer, color=MUTED, fontsize=8, ha="left", va="bottom")
    fig.patch.set_facecolor(SURFACE)
    fig.tight_layout(rect=(0, 0.04, 1, 0.90))
    title = getattr(fig, "_aq_title", None)
    if title:
        fig.text(0.015, 0.935, title, ha="left", va="center", color=INK, fontsize=12, fontweight="bold")
    fig.savefig(path, dpi=200, facecolor=SURFACE)


# ============================================================ main
def main():
    ap = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter, description=__doc__)
    ap.add_argument("--prepost")
    ap.add_argument("--log")
    ap.add_argument("--levels")
    ap.add_argument("--instrument", default=os.path.join(ROOT, "data", "Pre_Post_Test_Instrument.csv"))
    ap.add_argument("--bank", default=os.path.join(ROOT, "data", "AMR_Question_Bank.csv"))
    ap.add_argument("--out", default="results")
    ap.add_argument("--power-only", action="store_true")
    ap.add_argument("--seed", type=int, default=2026)
    a = ap.parse_args()

    os.makedirs(a.out, exist_ok=True)
    pw = power_table()
    pw.to_csv(os.path.join(a.out, "power_table.csv"), index=False)
    if a.power_only:
        print(pw.to_string(index=False))
        return

    if not a.prepost:
        ap.error("--prepost is required (or use --power-only)")
    for flag, path in (("--prepost", a.prepost), ("--log", a.log), ("--levels", a.levels)):
        if path and not os.path.exists(path):
            raise SystemExit(
                f"\nFile not found for {flag}: {path}\n"
                "The real pilot files do not exist until you collect data. To test the pipeline now, run:\n"
                "  python analysis/analysis.py --prepost data/synthetic/SYNTHETIC_Pre_Post_Test_Results.csv "
                "--log data/synthetic/SYNTHETIC_Gameplay_Answer_Log.csv "
                "--levels data/synthetic/SYNTHETIC_Gameplay_Analytics.csv --out results_synthetic\n"
                "After the pilot, save your data with the columns in data/templates/ and point the flags at those files.")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "DejaVu Sans"})
    charts = os.path.join(a.out, "charts")
    os.makedirs(charts, exist_ok=True)

    inst = pd.read_csv(a.instrument, keep_default_na=False)
    pp = pd.read_csv(a.prepost, keep_default_na=False, dtype=str)
    synthetic = "is_synthetic" in pp and (pp["is_synthetic"].astype(str) == "1").any()
    pp = pp[pp["consent_given"].str.upper().isin(["Y", "YES", "1", "TRUE"])].copy()

    know = inst[inst.Section == "knowledge"]
    att = inst[inst.Section == "attitude"]
    K, KEY = list(know.Item_ID), dict(zip(know.Item_ID, know.Correct_Response))
    KTOPIC = dict(zip(know.Item_ID, know.Topic))

    # ---- score items (correct = 1; wrong / Don't know / blank = 0)
    for ph in ("pre", "post"):
        for k in K:
            pp[f"{ph}_{k}_ok"] = (pp[f"{ph}_{k}"].str.strip().str.lower() == KEY[k].lower()).astype(int)
        pp[f"{ph}_knowledge"] = pp[[f"{ph}_{k}_ok" for k in K]].sum(axis=1)
        a_scores = []
        for _, it in att.iterrows():
            v = pd.to_numeric(pp[f"{ph}_{it.Item_ID}"], errors="coerce")
            a_scores.append(6 - v if it.Reverse_Scored == "yes" else v)
        pp[f"{ph}_attitude"] = pd.concat(a_scores, axis=1).sum(axis=1, min_count=len(att))

    complete = pp[pp[[f"post_{k}" for k in K]].ne("").all(axis=1) & pp[[f"pre_{k}" for k in K]].ne("").all(axis=1)]
    n_excluded = len(pp) - len(complete)
    d = complete
    n, kmax = len(d), len(K)
    pre, post = d["pre_knowledge"].astype(float).values, d["post_knowledge"].astype(float).values
    diff = post - pre

    # ---- primary hypothesis test
    sw = stats.shapiro(diff) if n >= 3 and diff.std() > 0 else None
    normal_ok = sw is not None and sw.pvalue >= ALPHA
    t1 = stats.ttest_rel(post, pre, alternative="greater")
    t2 = stats.ttest_rel(post, pre)
    nz = diff[diff != 0]
    w = stats.wilcoxon(post, pre, alternative="greater", zero_method="wilcox")
    ranks = stats.rankdata(np.abs(nz))
    r_rb = (ranks[nz > 0].sum() - ranks[nz < 0].sum()) / ranks.sum() if len(nz) else np.nan
    sd = diff.std(ddof=1)
    dz = diff.mean() / sd if sd > 0 else np.nan
    se = sd / np.sqrt(n)
    ci = (diff.mean() - stats.t.ppf(0.975, n - 1) * se, diff.mean() + stats.t.ppf(0.975, n - 1) * se)
    rng = np.random.default_rng(a.seed)
    boots = []
    for _ in range(5000):
        s = diff[rng.integers(0, n, n)]
        if s.std(ddof=1) > 0:
            boots.append(s.mean() / s.std(ddof=1))
    dz_ci = np.percentile(boots, [2.5, 97.5])
    g_class = (post.mean() - pre.mean()) / (kmax - pre.mean())
    primary = "paired t-test" if normal_ok else "Wilcoxon signed-rank"
    p_primary = t1.pvalue if normal_ok else w.pvalue

    hyp = pd.DataFrame([
        dict(measure="n participants (complete pre+post)", value=n),
        dict(measure="n excluded (incomplete)", value=n_excluded),
        dict(measure=f"pre-test mean (SD), out of {kmax}", value=f"{pre.mean():.2f} ({pre.std(ddof=1):.2f})"),
        dict(measure=f"post-test mean (SD), out of {kmax}", value=f"{post.mean():.2f} ({post.std(ddof=1):.2f})"),
        dict(measure="mean change (95% CI)", value=f"{diff.mean():.2f} ({ci[0]:.2f} to {ci[1]:.2f})"),
        dict(measure="median change (IQR)", value=f"{np.median(diff):.1f} ({np.percentile(diff,25):.1f} to {np.percentile(diff,75):.1f})"),
        dict(measure="Shapiro-Wilk on differences (W, p)", value=f"{sw.statistic:.3f}, {sw.pvalue:.4f}" if sw else "n/a"),
        dict(measure="paired t-test one-sided (t, df, p)", value=f"{t1.statistic:.3f}, {n-1}, {t1.pvalue:.2e}"),
        dict(measure="paired t-test two-sided p", value=f"{t2.pvalue:.2e}"),
        dict(measure="Wilcoxon signed-rank one-sided (W+, p)", value=f"{w.statistic:.1f}, {w.pvalue:.2e}"),
        dict(measure="rank-biserial r (Wilcoxon effect size)", value=f"{r_rb:.3f}"),
        dict(measure="Cohen's dz (bootstrap 95% CI)", value=f"{dz:.2f} ({dz_ci[0]:.2f} to {dz_ci[1]:.2f})"),
        dict(measure="class-average normalised gain <g>", value=f"{g_class:.2f}"),
        dict(measure="primary test (by pre-registered rule)", value=primary),
        dict(measure="primary p-value", value=f"{p_primary:.2e}"),
        dict(measure="decision at alpha = 0.05", value="reject H0" if p_primary < ALPHA else "fail to reject H0"),
        dict(measure="KR-20 reliability of knowledge test (pre)", value=f"{kr20(d[[f'pre_{k}_ok' for k in K]]):.2f}"),
    ])
    hyp.to_csv(os.path.join(a.out, "hypothesis_test.csv"), index=False)

    scores = d[["participant_id", "pre_knowledge", "post_knowledge", "pre_attitude", "post_attitude"]].copy()
    scores["knowledge_change"] = scores.post_knowledge - scores.pre_knowledge
    scores["normalised_gain"] = np.where(scores.pre_knowledge < kmax,
                                         scores.knowledge_change / (kmax - scores.pre_knowledge), np.nan)
    scores.to_csv(os.path.join(a.out, "Pre_Post_Scores.csv"), index=False)

    # ---- secondary: attitude
    att_ok = d[["pre_attitude", "post_attitude"]].dropna()
    att_w = stats.wilcoxon(att_ok.post_attitude, att_ok.pre_attitude, alternative="greater") if len(att_ok) > 5 else None

    # ---- secondary: topic-wise
    trows = []
    for t in dict.fromkeys(KTOPIC.values()):
        ks = [k for k in K if KTOPIC[k] == t]
        pre_t = d[[f"pre_{k}_ok" for k in ks]].sum(axis=1)
        post_t = d[[f"post_{k}_ok" for k in ks]].sum(axis=1)
        p = stats.wilcoxon(post_t, pre_t, alternative="greater").pvalue if (post_t - pre_t).abs().sum() else 1.0
        trows.append(dict(topic=TOPIC_LABELS.get(t, t), n_items=len(ks),
                          pre_accuracy_pct=round(100 * pre_t.mean() / len(ks), 1),
                          post_accuracy_pct=round(100 * post_t.mean() / len(ks), 1), p_wilcoxon=p))
    topics = pd.DataFrame(trows)
    topics["p_holm"] = holm(topics.p_wilcoxon)
    topics.to_csv(os.path.join(a.out, "topic_accuracy.csv"), index=False)

    # ---- secondary: item-level McNemar (exact)
    irows = []
    for k in K:
        b = int(((d[f"pre_{k}_ok"] == 0) & (d[f"post_{k}_ok"] == 1)).sum())   # wrong -> right
        c = int(((d[f"pre_{k}_ok"] == 1) & (d[f"post_{k}_ok"] == 0)).sum())   # right -> wrong
        p = stats.binomtest(b, b + c, 0.5).pvalue if b + c else 1.0
        irows.append(dict(item=k, topic=TOPIC_LABELS.get(KTOPIC[k]), statement=know.set_index("Item_ID").Item_EN[k],
                          pre_correct_pct=round(100 * d[f"pre_{k}_ok"].mean(), 1),
                          post_correct_pct=round(100 * d[f"post_{k}_ok"].mean(), 1),
                          pre_dont_know_pct=round(100 * (d[f"pre_{k}"].str.lower() == "don't know").mean(), 1),
                          wrong_to_right=b, right_to_wrong=c, p_mcnemar_exact=p))
    items = pd.DataFrame(irows)
    items["p_holm"] = holm(items.p_mcnemar_exact)
    items.to_csv(os.path.join(a.out, "item_prepost_mcnemar.csv"), index=False)

    # ---- gameplay
    have_game = a.log and a.levels and os.path.exists(a.log) and os.path.exists(a.levels)
    if have_game:
        log = pd.read_csv(a.log, keep_default_na=False)
        lv = pd.read_csv(a.levels, keep_default_na=False)
        bank = pd.read_csv(a.bank, keep_default_na=False).set_index("Question_ID")
        for col in ("level", "is_correct", "hint_used", "audio_played", "response_time_ms", "points_awarded"):
            log[col] = pd.to_numeric(log[col], errors="coerce")
        for col in ("level", "questions_attempted", "correct", "incorrect", "hints_used", "time_spent_sec",
                    "points", "level_completed"):
            lv[col] = pd.to_numeric(lv[col], errors="coerce")
        n_players = lv.participant_id.nunique()
        done = lv[lv.level_completed.fillna(0) == 1] if "level_completed" in lv else lv
        max_level = (done.groupby("participant_id")["level"].max()
                     .reindex(lv.participant_id.unique()).fillna(0))
        lsum = (lv.groupby("level").agg(players=("participant_id", "nunique"),
                                        median_time_sec=("time_spent_sec", "median"),
                                        hints_per_player=("hints_used", "mean")).reset_index())
        acc = log.groupby("level").is_correct.mean() * 100
        lsum["accuracy_pct"] = lsum["level"].map(acc).round(1)
        lsum["completed_pct_of_starters"] = lsum["level"].map(
            lambda L: round(100 * (max_level >= L).sum() / n_players, 1))
        lsum.to_csv(os.path.join(a.out, "level_summary.csv"), index=False)

        qd = log.groupby("question_id").agg(attempts=("is_correct", "size"), error_rate=("is_correct", lambda s: 1 - s.mean()),
                                            hint_rate=("hint_used", "mean"),
                                            median_rt_ms=("response_time_ms", "median")).reset_index()
        wrong = log[log.is_correct == 0]
        top_wrong = (wrong.groupby("question_id").selected_option
                     .agg(lambda s: s.value_counts().index[0]) if len(wrong) else pd.Series(dtype=str))
        qd["most_chosen_wrong_option"] = qd.question_id.map(top_wrong).fillna("")
        qd["wrong_option_text"] = [bank.loc[q, f"Option_{o}_EN"] if o else "" for q, o in
                                   zip(qd.question_id, qd.most_chosen_wrong_option)]
        qd["level"] = qd.question_id.map(bank.Level)
        qd["topic"] = qd.question_id.map(bank.Topic).map(TOPIC_LABELS)
        qd["question"] = qd.question_id.map(bank.Question_EN)
        qd = qd.sort_values("error_rate", ascending=False)
        qd["error_rate"] = (qd.error_rate * 100).round(1)
        qd.rename(columns={"error_rate": "error_rate_pct"}).to_csv(os.path.join(a.out, "question_difficulty.csv"), index=False)

        per_p = lv.groupby("participant_id").agg(levels_completed=("level", "max"), total_time_sec=("time_spent_sec", "sum"),
                                                  points=("points", "sum"), hints=("hints_used", "sum"))
        per_p["levels_completed"] = max_level
        per_p["game_accuracy"] = log.groupby("participant_id").is_correct.mean()
        m = scores.set_index("participant_id").join(per_p, how="inner")
        crows = []
        for x in ("levels_completed", "game_accuracy", "total_time_sec", "points", "hints"):
            for y in ("post_knowledge", "knowledge_change"):
                if m[x].nunique() > 1:
                    r = stats.spearmanr(m[x], m[y])
                    crows.append(dict(engagement_measure=x, outcome=y, spearman_rho=round(r.statistic, 3), p=r.pvalue, n=len(m)))
        corr = pd.DataFrame(crows)
        if len(corr):
            corr["p_holm"] = holm(corr.p)
        corr.to_csv(os.path.join(a.out, "engagement_correlation.csv"), index=False)

    # ============================================================ charts
    import matplotlib.pyplot as plt
    footer = f"n = {n}  |  knowledge score 0-{kmax}  |  data: {os.path.basename(a.prepost)}  |  generated {date.today()}"

    # 1. pre vs post mean with 95% CI
    fig, ax = plt.subplots(figsize=(6, 4.6))
    means = [pre.mean(), post.mean()]
    cis = [stats.t.ppf(0.975, n - 1) * x.std(ddof=1) / np.sqrt(n) for x in (pre, post)]
    bars = ax.bar(["Pre-test", "Post-test"], means, color=[PRE_C, POST_C], width=0.5,
                  edgecolor=SURFACE, linewidth=2)
    ax.errorbar([0, 1], means, yerr=cis, fmt="none", ecolor=INK2, elinewidth=1.2, capsize=5)
    for b, mval, c in zip(bars, means, cis):
        ax.text(b.get_x() + b.get_width() / 2, mval + c + 0.45, f"{mval:.1f}", ha="center", color=INK, fontsize=11)
    ax.set_ylim(0, kmax)
    style_axes(ax, f"Mean AMR knowledge score, before and after playing",
               ylabel=f"Score (0-{kmax}), error bars = 95% CI")
    finish(fig, os.path.join(charts, "1_pre_post_scores.png"), synthetic, footer)
    plt.close(fig)

    # 2. distribution of individual change
    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    lo, hi = int(diff.min()) - 1, int(diff.max()) + 1
    counts, _, _ = ax.hist(diff, bins=np.arange(lo, hi + 1) - 0.5, color=SINGLE_C, edgecolor=SURFACE,
                           linewidth=2, zorder=2)
    top_y = counts.max() * 1.22
    ax.set_ylim(0, top_y)
    ax.axvline(0, color=AXIS, linewidth=1.5, zorder=1)
    ax.axvline(diff.mean(), color=INK2, linewidth=1.5, linestyle="--", zorder=3)
    ax.text(diff.mean(), top_y * 0.97, f"  mean change {diff.mean():+.1f}", color=INK2, fontsize=9, va="top")
    style_axes(ax, "Change in knowledge score per participant", xlabel="Post-test minus pre-test (points)",
               ylabel="Participants")
    finish(fig, os.path.join(charts, "2_score_change_distribution.png"), synthetic, footer)
    plt.close(fig)

    # 3. topic-wise accuracy pre vs post (grouped bars, legend + direct labels)
    fig, ax = plt.subplots(figsize=(7.5, 4.6))
    x = np.arange(len(topics))
    wd = 0.36
    b1 = ax.bar(x - wd / 2, topics.pre_accuracy_pct, wd, color=PRE_C, label="Pre-test", edgecolor=SURFACE, linewidth=2)
    b2 = ax.bar(x + wd / 2, topics.post_accuracy_pct, wd, color=POST_C, label="Post-test", edgecolor=SURFACE, linewidth=2)
    for bars_ in (b1, b2):
        for b in bars_:
            ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 1.5, f"{b.get_height():.0f}%", ha="center",
                    color=INK2, fontsize=8)
    ax.set_xticks(x, [textwrap.fill(t, 14) for t in topics.topic])
    ax.set_ylim(0, 100)
    ax.legend(frameon=False, labelcolor=INK2, loc="lower left", ncol=2, bbox_to_anchor=(0, 1.0), fontsize=9)
    style_axes(ax, "Share of correct answers by topic", ylabel="% correct")
    finish(fig, os.path.join(charts, "3_topic_accuracy.png"), synthetic, footer)
    plt.close(fig)

    if have_game:
        # 4. level completion
        fig, ax = plt.subplots(figsize=(6.5, 4.2))
        labels = [f"Level {L}" for L in lsum["level"]]
        bars = ax.bar(labels, lsum.completed_pct_of_starters, color=SINGLE_C, width=0.55, edgecolor=SURFACE, linewidth=2)
        for b in bars:
            ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 1.5, f"{b.get_height():.0f}%", ha="center",
                    color=INK2, fontsize=9)
        ax.set_ylim(0, 108)
        style_axes(ax, "Players who completed each level", ylabel=f"% of {n_players} players")
        finish(fig, os.path.join(charts, "4_level_completion.png"), synthetic,
               f"n = {n_players} players  |  data: {os.path.basename(a.levels)}  |  generated {date.today()}")
        plt.close(fig)

        # 5. hardest in-game questions
        top = qd[qd.attempts >= 5].head(10).iloc[::-1]
        fig, ax = plt.subplots(figsize=(8, 4.8))
        ax.barh([f"{q}  {textwrap.shorten(t, 48, placeholder='...')}" for q, t in zip(top.question_id, top.question)],
                top.error_rate, color=SINGLE_C, edgecolor=SURFACE, linewidth=2, height=0.6)
        for i, v in enumerate(top.error_rate):
            ax.text(v + 1, i, f"{v:.0f}%", va="center", color=INK2, fontsize=8)
        ax.set_xlim(0, 100)
        style_axes(ax, "In-game questions with the highest error rates", xlabel="% of attempts answered wrongly")
        ax.yaxis.grid(False)
        ax.xaxis.grid(True, color=GRID, linewidth=0.8)
        finish(fig, os.path.join(charts, "5_hardest_questions.png"), synthetic,
               f"questions with >= 5 attempts  |  data: {os.path.basename(a.log)}  |  generated {date.today()}")
        plt.close(fig)

    # ============================================================ summary
    lines = []
    if synthetic:
        lines += ["> **SYNTHETIC DEMO DATA - these numbers are invented and must not be reported.**", ""]
    lowest = items.sort_values("pre_correct_pct").head(5)[["item", "statement", "pre_correct_pct",
                                                           "post_correct_pct", "p_holm"]].round(4)
    lines += [f"# Antibiotic Quest - pilot results ({date.today()})", "",
              "## Primary hypothesis (knowledge score)", "", md(hyp), "",
              f"**Primary test:** {primary} (rule: paired t-test if Shapiro-Wilk p >= 0.05 on the differences). "
              f"Report the effect size and CI, not only the p-value.", "",
              "## Attitude / intention score (secondary, range 6-30, higher = more prudent)", "",
              f"Pre mean {att_ok.pre_attitude.mean():.1f}, post mean {att_ok.post_attitude.mean():.1f}, "
              + (f"Wilcoxon one-sided p = {att_w.pvalue:.2e} (n = {len(att_ok)})." if att_w is not None else "n too small."), "",
              "## Topic-wise accuracy (exploratory, Holm-adjusted)", "", md(topics.round(4)), "",
              "## Items with the lowest pre-test accuracy", "", md(lowest), ""]
    if have_game:
        lines += ["## Gameplay", "", f"Players: {n_players}. Completed all 5 levels: "
                  f"{(max_level >= 5).mean() * 100:.0f}%.", "", md(lsum.round(1)), "",
                  "### Hardest in-game questions", "",
                  md(qd.head(5)[["question_id", "error_rate", "most_chosen_wrong_option", "wrong_option_text"]].round(1)), "",
                  "### Engagement vs learning (Spearman, exploratory)", "",
                  md(corr.round(4)) if len(corr) else "n/a", ""]
    lines += ["## Sample size reference (paired t-test, alpha 0.05, power 0.80)", "", md(pw), ""]
    with open(os.path.join(a.out, "summary.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("\n".join(lines[:40]))
    print(f"\nWrote tables to {a.out}/ and charts to {charts}/")


if __name__ == "__main__":
    main()

"""
A/B experiment analysis: AI-assisted onboarding (treatment) vs standard onboarding (control).

Primary metric: activation rate (onboarding_completed)
Secondary metrics: first project creation, AI adoption, D7 retention (proxy)
Guardrail: none simulated yet (would be error rate / latency / cost per user in a real run)

This module computes:
- absolute lift, relative lift
- two-proportion z-test (p-value)
- 95% confidence interval on the difference in proportions
- Cohen's h effect size

Run:
    python src/experimentation/ab_test.py
"""

import numpy as np
import pandas as pd
from scipy import stats


def two_proportion_z_test(success_a: int, n_a: int, success_b: int, n_b: int):
    """success_a/n_a = control, success_b/n_b = treatment.
    Returns dict with p1, p2, absolute_lift, relative_lift, ci_95, z_stat,
    p_value, cohens_h.
    """
    p1 = success_a / n_a
    p2 = success_b / n_b

    absolute_lift = p2 - p1
    relative_lift = absolute_lift / p1 if p1 > 0 else float("nan")

    # Pooled proportion for z-test under H0: p1 == p2
    p_pool = (success_a + success_b) / (n_a + n_b)
    se_pool = np.sqrt(
        p_pool * (1 - p_pool) * (1 / n_a + 1 / n_b)
    )

    z_stat = (p2 - p1) / se_pool if se_pool > 0 else float("nan")

    # Survival function is numerically stable for very small tail probabilities.
    # Using 1 - cdf(...) can underflow to exactly 0.0.
    p_value = 2 * stats.norm.sf(abs(z_stat))

    # Unpooled SE for the confidence interval on the difference
    se_diff = np.sqrt(
        p1 * (1 - p1) / n_a +
        p2 * (1 - p2) / n_b
    )

    ci_low = absolute_lift - 1.96 * se_diff
    ci_high = absolute_lift + 1.96 * se_diff

    # Cohen's h effect size for two proportions
    cohens_h = (
        2 * np.arcsin(np.sqrt(p2))
        - 2 * np.arcsin(np.sqrt(p1))
    )

    return {
        "control_rate_pct": round(100 * p1, 2),
        "treatment_rate_pct": round(100 * p2, 2),
        "absolute_lift_pp": round(100 * absolute_lift, 2),
        "relative_lift_pct": round(100 * relative_lift, 2),
        "ci_95_absolute_lift_pp": (
            round(100 * ci_low, 2),
            round(100 * ci_high, 2),
        ),
        "z_stat": round(z_stat, 3),
        "p_value": p_value,
        "cohens_h": round(cohens_h, 3),
        "n_control": n_a,
        "n_treatment": n_b,
    }


def required_sample_size(
    baseline_rate: float,
    min_detectable_effect: float,
    alpha: float = 0.05,
    power: float = 0.8,
) -> int:
    """Rough per-arm sample size for detecting an absolute lift of
    min_detectable_effect on top of baseline_rate, two-sided test.
    """
    p1 = baseline_rate
    p2 = baseline_rate + min_detectable_effect

    z_alpha = stats.norm.ppf(1 - alpha / 2)
    z_beta = stats.norm.ppf(power)

    p_bar = (p1 + p2) / 2

    numerator = (
        z_alpha * np.sqrt(2 * p_bar * (1 - p_bar))
        + z_beta
        * np.sqrt(
            p1 * (1 - p1) +
            p2 * (1 - p2)
        )
    ) ** 2

    denominator = (p2 - p1) ** 2

    return int(np.ceil(numerator / denominator))


def interpret(result: dict) -> str:
    """Produces a properly hedged interpretation.

    Guardrail metrics are not simulated in the current experiment, so this
    function does not claim that guardrails passed or failed.
    """
    sig = result["p_value"] < 0.05

    ci_low, ci_high = result["ci_95_absolute_lift_pp"]
    ci_excludes_zero = ci_low > 0 or ci_high < 0

    lines = []

    if sig and ci_excludes_zero:
        lines.append(
            f"The observed {result['absolute_lift_pp']}pp absolute lift "
            f"({result['relative_lift_pct']}% relative) is statistically "
            f"significant (p<0.001), and the 95% CI "
            f"[{ci_low}, {ci_high}]pp excludes zero."
        )
    else:
        lines.append(
            f"The observed {result['absolute_lift_pp']}pp lift did not "
            f"reach conventional significance (p={result['p_value']:.4g}); "
            f"the 95% CI [{ci_low}, {ci_high}]pp includes zero, so we "
            f"cannot rule out no true effect."
        )

    lines.append(
        f"Effect size (Cohen's h = {result['cohens_h']}) should be weighed "
        f"alongside statistical significance -- a significant but small "
        f"effect may not justify rollout cost."
    )

    lines.append(
        "Guardrail metrics (cost/user, latency, error rate) were not "
        "simulated in this experiment, so no guardrail conclusion is made."
    )

    lines.append(
        "This recommendation should combine statistical evidence with "
        "guardrail metrics and business cost -- not rest on the p-value alone."
    )

    return " ".join(lines)


if __name__ == "__main__":
    users = pd.read_csv(
        "data/raw/users.csv",
        parse_dates=["signup_date"],
    )

    clean_events = pd.read_csv(
        "data/processed/clean_events.csv",
        parse_dates=["timestamp"],
    )

    activated_users = set(
        clean_events.loc[
            clean_events["event_name"] == "onboarding_completed",
            "user_id",
        ]
    )

    users["activated"] = users["user_id"].isin(activated_users)

    control = users[
        users["experiment_group"] == "control"
    ]

    treatment = users[
        users["experiment_group"] == "treatment"
    ]

    result = two_proportion_z_test(
        success_a=int(control["activated"].sum()),
        n_a=len(control),
        success_b=int(treatment["activated"].sum()),
        n_b=len(treatment),
    )

    print(
        "=== A/B Test: AI-assisted onboarding vs control "
        "(Activation Rate) ==="
    )

    for k, v in result.items():
        if k == "p_value":
            if v < 0.001:
                print(f"{k}: <0.001")
            else:
                print(f"{k}: {v:.4g}")
        else:
            print(f"{k}: {v}")

    print("\n=== Interpretation ===")
    print(interpret(result))

    print("\n=== Sample size check (for future experiments) ===")

    n_needed = required_sample_size(
        baseline_rate=0.62,
        min_detectable_effect=0.05,
    )

    print(
        f"To detect a 5pp lift on a 62% baseline at 80% power, "
        f"alpha=0.05: ~{n_needed} users per arm"
    )
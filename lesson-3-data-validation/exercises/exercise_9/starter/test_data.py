import scipy.stats
import pandas as pd


# COMPLETE HERE: make this test accept the fixtures defined in the
# conftest.py file (data and ks_alpha)
def test_kolmogorov_smirnov(data, ks_alpha):

    sample1, sample2 = data

    columns = [
        "danceability",
        "energy",
        "loudness",
        "speechiness",
        "acousticness",
        "instrumentalness",
        "liveness",
        "valence",
        "tempo",
        "duration_ms"
    ]

    # Bonferroni correction for multiple hypothesis testing
    # (see my blog post on this topic to see where this comes from:
    # https://towardsdatascience.com/precision-and-recall-trade-off-and-multiple-hypothesis-testing-family-wise-error-rate-vs-false-71a85057ca2b)
    alpha_prime = 1 - (1 - ks_alpha)**(1 / len(columns))

    for col in columns:

        ts, p_value = scipy.stats.ks_2samp(sample1[col], sample2[col])

        # NOTE: as always, the p-value should be interpreted as the probability of
        # obtaining a test statistic (TS) equal or more extreme that the one we got
        # by chance, when the null hypothesis is true. If this probability is not
        # large enough, this dataset should be looked at carefully, hence we fail
        #assert p_value > alpha_prime

        # TODO: REMOVE THIS AND MOVE IT TO THE INFERANCE PIPELINE
        #drop na and check if p_value is greater than alpha_prime
        p_value = p_value if not pd.isna(p_value) else 1.0
        assert p_value > alpha_prime, f"KS test failed for column {col}: p_value={p_value}, alpha_prime={alpha_prime}"
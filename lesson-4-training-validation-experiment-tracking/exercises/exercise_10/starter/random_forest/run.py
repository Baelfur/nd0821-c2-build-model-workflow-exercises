#!/usr/bin/env python
import os
import argparse
import logging
import json

import pandas as pd
import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import roc_auc_score, confusion_matrix, ConfusionMatrixDisplay
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OrdinalEncoder, StandardScaler, FunctionTransformer
import matplotlib.pyplot as plt
import wandb
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.impute import SimpleImputer


logging.basicConfig(level=logging.INFO, format="%(asctime)-15s %(message)s")
logger = logging.getLogger()


def go(args):

    run = wandb.init(project="exercise_10", job_type="train")

    logger.info("Downloading and reading test artifact")
    train_data_path = run.use_artifact(args.train_data).file()
    df = pd.read_csv(train_data_path, low_memory=False)

    # Extract the target from the features
    logger.info("Extracting target from dataframe")
    X = df.copy()
    y = X.pop("genre")

    logger.info("Splitting train/val")
    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.3, stratify=y, random_state=42
    )

    logger.info("Setting up pipeline")

    pipe = get_inference_pipeline(args)

    logger.info("Fitting")
    pipe.fit(X_train, y_train)

    logger.info("Scoring")
    score = roc_auc_score(
        y_val, pipe.predict_proba(X_val), average="macro", multi_class="ovo"
    )

    run.summary["AUC"] = score

    # We collect the feature importance for all non-nlp features first
    feat_names = np.array(
        pipe["preprocessor"].transformers[0][-1]
        + pipe["preprocessor"].transformers[1][-1]
    )
    feat_imp = pipe["classifier"].feature_importances_[: len(feat_names)]

    # For the NLP feature we sum across all the TF-IDF dimensions into a global
    # NLP importance
    nlp_importance = sum(pipe["classifier"].feature_importances_[len(feat_names) :])

    feat_imp = np.append(feat_imp, nlp_importance)
    feat_names = np.append(feat_names, "title + song_name")

    fig_feat_imp, sub_feat_imp = plt.subplots(figsize=(10, 10))
    idx = np.argsort(feat_imp)[::-1]
    sub_feat_imp.bar(range(feat_imp.shape[0]), feat_imp[idx], color="r", align="center")
    _ = sub_feat_imp.set_xticks(range(feat_imp.shape[0]))
    _ = sub_feat_imp.set_xticklabels(feat_names[idx], rotation=90)

    fig_feat_imp.tight_layout()

    fig_cm, sub_cm = plt.subplots(figsize=(10, 10))

    y_pred = pipe.predict(X_val)

    cm = confusion_matrix(
                y_true=y_val,
                y_pred=y_pred,
                labels=pipe["classifier"].classes_,
                normalize="true"
            )

    disp  = ConfusionMatrixDisplay(
                    confusion_matrix=cm,
                    display_labels=pipe["classifier"].classes_
                )

    disp.plot(
        ax=sub_cm,
        values_format=".1f",
        xticks_rotation=90,
    )

    fig_cm.tight_layout()

    run.log(
        {
            "feature_importance": wandb.Image(fig_feat_imp),
            "confusion_matrix": wandb.Image(fig_cm),
        }
    )


def get_inference_pipeline(args):
    # Our pipeline will contain a pre-processing step and a Random Forest.
    # The pre-processing step will impute missing values, encode the labels,
    # normalize numerical features and compute a TF-IDF for the textual
    # feature

    # We need 3 separate preprocessing "tracks":
    # - one for categorical features
    # - one for numerical features
    # - one for textual ("nlp") features

    # Categorical preprocessing pipeline.
    # NOTE: we sort the list so that the order of the columns will be
    # defined, and not dependent on the order in the input dataset
    categorical_features = sorted(["time_signature", "key"])
    categorical_transformer = make_pipeline(
        SimpleImputer(strategy="constant", fill_value=0), OrdinalEncoder()
    )

    # Numerical preprocessing pipeline
    numeric_features = sorted([
        "danceability",
        "energy",
        "loudness",
        "speechiness",
        "acousticness",
        "instrumentalness",
        "liveness",
        "valence",
        "tempo",
        "duration_ms",
    ])

    ############# YOUR CODE HERE
    # USE make_pipeline to create a pipeline containing a SimpleImputer using strategy=median
    # and a StandardScaler (you can use the default options for the latter) 
    numeric_transformer = make_pipeline(
        SimpleImputer(strategy="median"), StandardScaler()
    )

    # Textual ("nlp") preprocessing pipeline
    nlp_features = ["text_feature"]
    # This trick is needed because SimpleImputer wants a 2d input, but
    # TfidfVectorizer wants a 1d input. So we reshape in between the two steps
    reshape_to_1d = FunctionTransformer(np.reshape, kw_args={"newshape": -1})

    ############# YOUR CODE HERE
    # USE make_pipeline to create a pipeline containing a SimpleImputer with strategy=constant and
    # fill_value="" (the empty string), followed by our custom reshape_to_1d instance, and finally
    # insert a TfidfVectorizer with the options binary=True
    nlp_transformer = make_pipeline(
        SimpleImputer(strategy="constant", fill_value=""),
        reshape_to_1d,
        TfidfVectorizer(binary=True),
    )

    # Put the 3 tracks together into one pipeline using the ColumnTransformer
    # This also drops the columns that we are not explicitly transforming
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_transformer, numeric_features),
            ("cat", categorical_transformer, categorical_features), # COMPLETE HERE using the categorical transformer and the categorical_features,
            ("nlp1", nlp_transformer, nlp_features),
        ],
        remainder="drop",  # This drops the columns that we do not transform (i.e., we don't use)
    )

    # Get the configuration for the model
    with open(args.model_config) as fp:
        model_config = json.load(fp)
    # Add it to the W&B configuration so the values for the hyperparams
    # are tracked
    wandb.config.update(model_config)

    ############# YOUR CODE HERE
    # Append classifier to preprocessing pipeline.
    # Now we have a full prediction pipeline.
    # CREATE a Pipeline instances with 2 steps: one step called "preprocessor" using the
    # preprocessor instance, and another one called "classifier" using RandomForestClassifier(**model_config)
    # (i.e., a Random Forest with the configuration we have received as input)
    # NOTE: here you should create the Pipeline object directly, and not make_pipeline
    # HINT: Pipeline(steps=[("preprocessor", instance1), ("classifier", LogisticRegression)]) creates a
    #       Pipeline with two steps called "preprocessor" and "classifier" using the sklearn instances instance1
    #       as preprocessor and a LogisticRegression as classifier
    pipe = Pipeline(steps=[
        ("preprocessor", preprocessor),
        ("classifier", RandomForestClassifier(**model_config)),
    ])
    return pipe


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Train a Random Forest",
        fromfile_prefix_chars="@",
    )

    parser.add_argument(
        "--train_data",
        type=str,
        help="Fully-qualified name for the training data artifact",
        required=True,
    )

    parser.add_argument(
        "--model_config",
        type=str,
        help="Path to a JSON file containing the configuration for the random forest",
        required=True,
    )

    args = parser.parse_args()

    go(args)

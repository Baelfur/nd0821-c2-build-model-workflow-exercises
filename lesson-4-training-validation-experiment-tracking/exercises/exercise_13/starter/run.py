#!/usr/bin/env python
import argparse
import logging
import pandas as pd
import wandb
import mlflow.sklearn
import matplotlib.pyplot as plt
from sklearn.metrics import roc_auc_score, confusion_matrix, ConfusionMatrixDisplay

logging.basicConfig(level=logging.INFO, format="%(asctime)-15s %(message)s")
logger = logging.getLogger()


def go(args):

    run = wandb.init(project="exercise_13", job_type="test")

    logger.info("Downloading and reading test artifact")
    ## Get the args.test_data artifact from W&B locally
    test_data_path = run.use_artifact(args.test_data).file()
    df = pd.read_csv(test_data_path, low_memory=False)

    # Extract the target from the features
    logger.info("Extracting target from dataframe")
    X_test = df.copy()
    y_test = X_test.pop("genre")

    logger.info("Downloading and reading the exported model")

    ## Get the args.model_export artifact from W&B locally. Since this artifact contains a directory
    # and not a single file, you will have to use .download() instead of .file()
    model_export_path = run.use_artifact(args.model_export).download()

    # Load the model using mlflow.sklearn.load_model
    pipe = mlflow.sklearn.load_model(model_export_path)

    # Compute the prediction from the model using .predict_proba on the test set
    pred_proba = pipe.predict_proba(X_test)

    logger.info("Scoring")
    score = roc_auc_score(y_test, pred_proba, average="macro", multi_class="ovo")

    run.summary["AUC"] = score

    logger.info("Computing confusion matrix")
    fig_cm, sub_cm = plt.subplots(figsize=(10, 10))

    y_pred = pipe.predict(X_test)

    cm = confusion_matrix(
                y_true=y_test,
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
            "confusion_matrix": wandb.Image(fig_cm)
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Test the provided model on the test artifact",
        fromfile_prefix_chars="@",
    )

    parser.add_argument(
        "--model_export",
        type=str,
        help="Fully-qualified artifact name for the exported model to evaluate",
        required=True,
    )

    parser.add_argument(
        "--test_data",
        type=str,
        help="Fully-qualified artifact name for the test data",
        required=True,
    )

    args = parser.parse_args()

    go(args)

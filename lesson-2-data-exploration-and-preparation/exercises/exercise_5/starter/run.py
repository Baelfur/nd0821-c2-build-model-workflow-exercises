#!/usr/bin/env python
import argparse
import logging
import os

import pandas as pd
import wandb


logging.basicConfig(level=logging.INFO, format="%(asctime)-15s %(message)s")
logger = logging.getLogger()


def go(args):

    run = wandb.init(project="exercise_5", job_type="process_data")

    logger.info("Downloading artifact")
    artifact = run.use_artifact(args.input_artifact)
    artifact_path = artifact.file()
    
    df= pd.read_parquet(artifact_path)
    # Drop the duplicates
    
    logger.info("Dropping duplicates")
    df = df.drop_duplicates().reset_index(drop=True)
    
    logger.info("Fixing missing values in Title")
    df['title'].fillna(value='', inplace=True)
    logger.info("Fixing missing values in Song Name")
    df['song_name'].fillna(value='', inplace=True)
    
    # lesson 8 is shitting the bed because of nans in all numerical columns, stubbing out a dataclean to drop rows with nans in any of the numerical columns
    """
    logger.info("Dropping rows with NaN in numerical columns")
    
    numerical_columns = [
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
    df = df.dropna(subset=[col for col in numerical_columns if col in df.columns])
    logger.info("Dropped rows with NaN in numerical columns")
    """
    # If you want to keep the rows with NaN in numerical columns, you can comment out the above lines
    
    
    logger.info("Creating text feature")
    df['text_feature'] = df['title'] + ' ' + df['song_name']
    
    filename = args.artifact_name
    logger.info("Saving processed data to CSV")
    df.to_csv(filename, index=False)
    
    artifact = wandb.Artifact(
        name=args.artifact_name,
        type=args.artifact_type,
        description=args.artifact_description,
    )
    artifact.add_file(filename)
    
    logger.info("Logging artifact")
    run.log_artifact(artifact)
    
    logger.info("Removing local file")
    os.remove(filename)


if __name__ == "__main__":#
    parser = argparse.ArgumentParser(
        description="Preprocess a dataset",
        fromfile_prefix_chars="@",
    )

    parser.add_argument(
        "--input_artifact",
        type=str,
        help="Fully-qualified name for the input artifact",
        required=True,
    )

    parser.add_argument(
        "--artifact_name", type=str, help="Name for the artifact", required=True
    )

    parser.add_argument(
        "--artifact_type", type=str, help="Type for the artifact", required=True
    )

    parser.add_argument(
        "--artifact_description",
        type=str,
        help="Description for the artifact",
        required=True,
    )

    args = parser.parse_args()

    go(args)

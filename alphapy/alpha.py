################################################################################
#
# Package   : AlphaPy
# Module    : alpha_sport
# Version   : 1.0
# Date      : July 11, 2013
#
# Copyright 2017 @ Alpha314
# Mark Conway & Robert D. Scott II
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Example: python ../AlphaPy/alpha.py -d './config'
#
################################################################################


#
# Imports
#

from __future__ import division
import argparse
from data import get_data
from data import sample_data
from data import shuffle_data
from estimators import get_estimators
from estimators import ModelType
from estimators import scorers
from features import create_features
from features import create_interactions
from features import drop_features
from features import remove_lv_features
from features import save_features
from features import select_features
from globs import CSEP
from globs import PSEP
from globs import SSEP
from globs import WILDCARD
import logging
from model import first_fit
from model import generate_metrics
from model import get_model_config
from model import get_sample_weights
from model import load_model_object
from model import make_predictions
from model import Model
from model import predict_best
from model import predict_blend
from model import save_model
import numpy as np
from optimize import hyper_grid_search
from optimize import rfe_search
from optimize import rfecv_search
import pandas as pd
from plots import generate_plots
import yaml


#
# Initialize logger
#

logger = logging.getLogger(__name__)


#
# Function data_pipeline
#

def data_pipeline(model):
    """
    AlphaPy Data Pipeline
    :rtype : model object
    """

    logger.info("DATA PIPELINE")

    # Unpack the model specifications

    drop = model.specs['drop']
    target = model.specs['target']
    test_labels = model.specs['test_labels']

    # Get train and test data

    X_train, y_train = get_data(model, 'train')
    X_test, y_test = get_data(model, 'test')

    # Drop features

    X_train = drop_features(X_train, drop)
    X_test = drop_features(X_test, drop)

    # Log feature statistics

    logger.info("Original Feature Statistics")
    logger.info("Number of Training Rows    : %d", X_train.shape[0])
    logger.info("Number of Training Columns : %d", X_train.shape[1])
    uv, uc = np.unique(y_train, return_counts=True)
    logger.info("Unique Training Values for %s : %s", target, uv)
    logger.info("Unique Training Counts for %s : %s", target, uc)
    logger.info("Number of Testing Rows     : %d", X_test.shape[0])
    logger.info("Number of Testing Columns  : %d", X_test.shape[1])
    if test_labels:
        uv, uc = np.unique(y_test, return_counts=True)
        logger.info("Unique Testing Values for %s : %s", target, uv)
        logger.info("Unique Testing Counts for %s : %s", target, uc)

    # Merge training and test data

    if X_train.shape[1] == X_test.shape[1]:
        split_point = X_train.shape[0]
        X = pd.concat([X_train, X_test])
    else:
        raise IndexError("The number of training and test columns [%s, %s] must match.",
                         X_train.shape[1], X_test.shape[1])

    # Create initial features

    new_features = create_features(X, model, split_point, y_train)
    X_train, X_test = np.array_split(new_features, [split_point])
    model = save_features(model, X_train, X_test, y_train, y_test)

    # Generate interactions

    all_features = create_interactions(new_features, model)
    X_train, X_test = np.array_split(all_features, [split_point])
    model = save_features(model, X_train, X_test)

    # Remove low-variance features

    sig_features = remove_lv_features(all_features)

    # Save the model's feature set

    logger.info("Feature Names : %s", sig_features.dtype.names)
    X_train, X_test = np.array_split(sig_features, [split_point])
    model = save_features(model, X_train, X_test)

    # Return the model
    return model


#
# Function model_pipeline
#

def model_pipeline(model):
    """
    AlphaPy Model Pipeline
    :rtype : model object
    """

    logger.info("MODEL PIPELINE")

    # Unpack the model specifications

    calibration = model.specs['calibration']
    feature_selection = model.specs['feature_selection']
    grid_search = model.specs['grid_search']
    rfe = model.specs['rfe']
    sampling = model.specs['sampling']
    scorer = model.specs['scorer']
    test_labels = model.specs['test_labels']

    # Shuffle the data [if specified]

    model = shuffle_data(model)

    # Oversampling or Undersampling [if specified]

    if sampling:
        model = sample_data(model)
    else:
        logger.info("Skipping Sampling")

    # Get sample weights

    model = get_sample_weights(model)

    # Get the available classifiers and regressors 

    logger.info("Getting All Estimators")
    estimators = get_estimators(model)

    # Get the available scorers

    if scorer not in scorers:
        raise KeyError("Scorer function %s not found", scorer)

    # Model Selection

    logger.info("Selecting Models")

    for algo in model.algolist:
        logger.info("Algorithm: %s", algo)
        # select estimator
        try:
            estimator = estimators[algo]
            scoring = estimator.scoring
            est = estimator.estimator
        except KeyError:
            logger.info("Algorithm %s not found", algo)
        # feature selection
        if feature_selection and not grid_search:
            model = select_features(model)
        # initial fit
        model = first_fit(model, algo, est)
        # recursive feature elimination
        if rfe:
            if scoring:
                model = rfecv_search(model, algo)
            elif hasattr(est, "coef_"):
                model = rfe_search(model, algo)
            else:
                logger.info("No RFE Available for %s", algo)
        # grid search
        if grid_search:
            model = hyper_grid_search(model, estimator)
        # predictions
        model = make_predictions(model, algo, calibration)

    # Create a blended estimator

    if len(model.algolist) > 1:
        model = predict_blend(model)

    # Generate metrics

    model = generate_metrics(model, 'train')
    model = generate_metrics(model, 'test')

    # Store the best estimator

    model = predict_best(model)

    # Generate plots

    generate_plots(model, 'train')
    if test_labels:
        generate_plots(model, 'test')

    # Save best features and predictions

    save_model(model, 'BEST', 'test')

    # Return the model
    return model


#
# Function score_with_model
#

def score_with_model(model):
    """
    AlphaPy Scoring
    """

    logger.info("SCORING")

    # Unpack the model data

    X_test = model.X_test

    # Unpack the model specifications

    directory = model.specs['directory']
    model_type = model.specs['model_type']

    # Load model object

    predictor = load_model_object(directory)

    # Score the test data
    
    preds = predictor.predict(X_test)
    logger.info("Predictions: %s", preds)
    if model_type == ModelType.classification:
        probas = predictor.predict_proba(X_test)[:, 1]
        logger.info("Probabilities: %s", probas)


#
# Function main_pipeline
#

def main_pipeline(model):
    """
    AlphaPy Main Pipeline
    :rtype : model object
    """

    # Unpack the model specifications

    scoring_mode = model.specs['scoring_mode']

    # Call the data pipeline

    model = data_pipeline(model)

    # Scoring Only or Calibration

    if scoring_mode:
        score_with_model(model)
    else:
        model = model_pipeline(model)

    # Return the completed model

    return model


#
# MAIN PROGRAM
#

if __name__ == '__main__':

    # Logging

    logging.basicConfig(format="[%(asctime)s] %(levelname)s\t%(message)s",
                        filename="alpha314.log", filemode='a', level=logging.DEBUG,
                        datefmt='%m/%d/%y %H:%M:%S')
    formatter = logging.Formatter("[%(asctime)s] %(levelname)s\t%(message)s",
                                  datefmt='%m/%d/%y %H:%M:%S')
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    console.setLevel(logging.INFO)
    logging.getLogger().addHandler(console)

    # Start the pipeline

    logger.info('*'*80)
    logger.info("START PIPELINE")
    logger.info('*'*80)

    # Argument Parsing

    parser = argparse.ArgumentParser(description="Alpha314 Parser")
    parser.add_argument("-d", dest="cfg_dir", default=".",
                        help="directory location of configuration file")
    args = parser.parse_args()

    # Read configuration file

    specs = get_model_config(args.cfg_dir)

    # Debug the program

    logger.debug('\n' + '='*50 + '\n')

    # Create a model from the arguments

    logger.info("Creating Model")

    model = Model(specs)

    # Start the pipeline

    logger.info("Calling Pipeline")

    model = main_pipeline(model)

    # Complete the pipeline

    logger.info('*'*80)
    logger.info("END PIPELINE")
    logger.info('*'*80)
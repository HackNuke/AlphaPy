################################################################################
#
# Package   : AlphaPy
# Module    : __main__
# Created   : July 11, 2013
#
# Copyright 2017 ScottFree Analytics LLC
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
# Example: alphapy -d './config'
#
################################################################################


#
# Imports
#

from alphapy.data import get_data
from alphapy.data import sample_data
from alphapy.data import shuffle_data
from alphapy.estimators import get_estimators
from alphapy.estimators import ModelType
from alphapy.estimators import scorers
from alphapy.features import create_features
from alphapy.features import create_interactions
from alphapy.features import drop_features
from alphapy.features import remove_lv_features
from alphapy.features import save_features
from alphapy.features import select_features
from alphapy.globs import CSEP, PSEP, SSEP
from alphapy.globs import WILDCARD
from alphapy.model import first_fit
from alphapy.model import generate_metrics
from alphapy.model import get_model_config
from alphapy.model import get_sample_weights
from alphapy.model import load_model_object
from alphapy.model import make_predictions
from alphapy.model import Model
from alphapy.model import predict_best
from alphapy.model import predict_blend
from alphapy.model import save_model
from alphapy.optimize import hyper_grid_search
from alphapy.optimize import rfe_search
from alphapy.optimize import rfecv_search
from alphapy.plots import generate_plots

import argparse
import logging
import numpy as np
import pandas as pd


#
# Initialize logger
#

logger = logging.getLogger(__name__)


#
# Function data_pipeline
#

def data_pipeline(model):
    r"""AlphaPy Data Pipeline

    Several sentences providing an extended description. Refer to
    variables using back-ticks, e.g. `var`.

    Parameters
    ----------
    var1 : array_like
        Array_like means all those objects -- lists, nested lists, etc. --
        that can be converted to an array.  We can also refer to
        variables like `var1`.
    var2 : int
        The type above can either refer to an actual Python type
        (e.g. ``int``), or describe the type of the variable in more
        detail, e.g. ``(N,) ndarray`` or ``array_like``.
    long_var_name : {'hi', 'ho'}, optional
        Choices in brackets, default first when optional.

    Returns
    -------
    type
        Explanation of anonymous return value of type ``type``.
    describe : type
        Explanation of return value named `describe`.
    out : type
        Explanation of `out`.

    Other Parameters
    ----------------
    only_seldom_used_keywords : type
        Explanation
    common_parameters_listed_above : type
        Explanation

    Raises
    ------
    BadException
        Because you shouldn't have done that.

    See Also
    --------
    otherfunc : relationship (optional)
    newfunc : Relationship (optional), which could be fairly long, in which
              case the line wraps here.
    thirdfunc, fourthfunc, fifthfunc

    Notes
    -----
    Notes about the implementation algorithm (if needed).

    This can have multiple paragraphs.

    You may include some math:

    .. math:: X(e^{j\omega } ) = x(n)e^{ - j\omega n}

    And even use a greek symbol like :math:`omega` inline.

    References
    ----------
    Cite the relevant literature, e.g. [1]_.  You may also cite these
    references in the notes section above.

    .. [1] O. McNoleg, "The integration of GIS, remote sensing,
       expert systems and adaptive co-kriging for environmental habitat
       modelling of the Highland Haggis using object-oriented, fuzzy-logic
       and neural-network techniques," Computers & Geosciences, vol. 22,
       pp. 585-588, 1996.

    Examples
    --------
    These are written in doctest format, and should illustrate how to
    use the function.

    >>> a = [1, 2, 3]
    >>> print [x + 3 for x in a]
    [4, 5, 6]
    >>> print "a\n\nb"
    a
    b

    """

    logger.info("DATA PIPELINE")

    # Unpack the model specifications

    drop = model.specs['drop']
    model_type = model.specs['model_type']
    target = model.specs['target']
    test_labels = model.specs['test_labels']

    # Get train and test data

    X_train, y_train = get_data(model, 'train')
    X_test, y_test = get_data(model, 'test')

    # Drop features

    logger.info("Dropping Features: %s", drop)
    X_train = drop_features(X_train, drop)
    X_test = drop_features(X_test, drop)

    # Log feature statistics

    logger.info("Original Feature Statistics")
    logger.info("Number of Training Rows    : %d", X_train.shape[0])
    logger.info("Number of Training Columns : %d", X_train.shape[1])
    if model_type == ModelType.classification:
        uv, uc = np.unique(y_train, return_counts=True)
        logger.info("Unique Training Values for %s : %s", target, uv)
        logger.info("Unique Training Counts for %s : %s", target, uc)
    logger.info("Number of Testing Rows     : %d", X_test.shape[0])
    logger.info("Number of Testing Columns  : %d", X_test.shape[1])
    if model_type == ModelType.classification and test_labels:
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

    X_train, X_test = np.array_split(sig_features, [split_point])
    model = save_features(model, X_train, X_test)

    # Return the model
    return model


#
# Function model_pipeline
#

def model_pipeline(model):
    r"""AlphaPy Model Pipeline

    Several sentences providing an extended description. Refer to
    variables using back-ticks, e.g. `var`.

    Parameters
    ----------
    var1 : array_like
        Array_like means all those objects -- lists, nested lists, etc. --
        that can be converted to an array.  We can also refer to
        variables like `var1`.
    var2 : int
        The type above can either refer to an actual Python type
        (e.g. ``int``), or describe the type of the variable in more
        detail, e.g. ``(N,) ndarray`` or ``array_like``.
    long_var_name : {'hi', 'ho'}, optional
        Choices in brackets, default first when optional.

    Returns
    -------
    type
        Explanation of anonymous return value of type ``type``.
    describe : type
        Explanation of return value named `describe`.
    out : type
        Explanation of `out`.

    Other Parameters
    ----------------
    only_seldom_used_keywords : type
        Explanation
    common_parameters_listed_above : type
        Explanation

    Raises
    ------
    BadException
        Because you shouldn't have done that.

    See Also
    --------
    otherfunc : relationship (optional)
    newfunc : Relationship (optional), which could be fairly long, in which
              case the line wraps here.
    thirdfunc, fourthfunc, fifthfunc

    Notes
    -----
    Notes about the implementation algorithm (if needed).

    This can have multiple paragraphs.

    You may include some math:

    .. math:: X(e^{j\omega } ) = x(n)e^{ - j\omega n}

    And even use a greek symbol like :math:`omega` inline.

    References
    ----------
    Cite the relevant literature, e.g. [1]_.  You may also cite these
    references in the notes section above.

    .. [1] O. McNoleg, "The integration of GIS, remote sensing,
       expert systems and adaptive co-kriging for environmental habitat
       modelling of the Highland Haggis using object-oriented, fuzzy-logic
       and neural-network techniques," Computers & Geosciences, vol. 22,
       pp. 585-588, 1996.

    Examples
    --------
    These are written in doctest format, and should illustrate how to
    use the function.

    >>> a = [1, 2, 3]
    >>> print [x + 3 for x in a]
    [4, 5, 6]
    >>> print "a\n\nb"
    a
    b

    """

    logger.info("MODEL PIPELINE")

    # Unpack the model specifications

    calibration = model.specs['calibration']
    feature_selection = model.specs['feature_selection']
    grid_search = model.specs['grid_search']
    model_type = model.specs['model_type']
    rfe = model.specs['rfe']
    sampling = model.specs['sampling']
    scorer = model.specs['scorer']
    test_labels = model.specs['test_labels']

    # Shuffle the data [if specified]

    model = shuffle_data(model)

    # Oversampling or Undersampling [if specified]

    if model_type == ModelType.classification:
        if sampling:
            model = sample_data(model)
        else:
            logger.info("Skipping Sampling")
        # Get sample weights (classification only)
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
        if feature_selection:
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
    r"""AlphaPy Scoring

    Several sentences providing an extended description. Refer to
    variables using back-ticks, e.g. `var`.

    Parameters
    ----------
    var1 : array_like
        Array_like means all those objects -- lists, nested lists, etc. --
        that can be converted to an array.  We can also refer to
        variables like `var1`.
    var2 : int
        The type above can either refer to an actual Python type
        (e.g. ``int``), or describe the type of the variable in more
        detail, e.g. ``(N,) ndarray`` or ``array_like``.
    long_var_name : {'hi', 'ho'}, optional
        Choices in brackets, default first when optional.

    Returns
    -------
    type
        Explanation of anonymous return value of type ``type``.
    describe : type
        Explanation of return value named `describe`.
    out : type
        Explanation of `out`.

    Other Parameters
    ----------------
    only_seldom_used_keywords : type
        Explanation
    common_parameters_listed_above : type
        Explanation

    Raises
    ------
    BadException
        Because you shouldn't have done that.

    See Also
    --------
    otherfunc : relationship (optional)
    newfunc : Relationship (optional), which could be fairly long, in which
              case the line wraps here.
    thirdfunc, fourthfunc, fifthfunc

    Notes
    -----
    Notes about the implementation algorithm (if needed).

    This can have multiple paragraphs.

    You may include some math:

    .. math:: X(e^{j\omega } ) = x(n)e^{ - j\omega n}

    And even use a greek symbol like :math:`omega` inline.

    References
    ----------
    Cite the relevant literature, e.g. [1]_.  You may also cite these
    references in the notes section above.

    .. [1] O. McNoleg, "The integration of GIS, remote sensing,
       expert systems and adaptive co-kriging for environmental habitat
       modelling of the Highland Haggis using object-oriented, fuzzy-logic
       and neural-network techniques," Computers & Geosciences, vol. 22,
       pp. 585-588, 1996.

    Examples
    --------
    These are written in doctest format, and should illustrate how to
    use the function.

    >>> a = [1, 2, 3]
    >>> print [x + 3 for x in a]
    [4, 5, 6]
    >>> print "a\n\nb"
    a
    b

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
    r"""AlphaPy Main Pipeline

    Several sentences providing an extended description. Refer to
    variables using back-ticks, e.g. `var`.

    Parameters
    ----------
    var1 : array_like
        Array_like means all those objects -- lists, nested lists, etc. --
        that can be converted to an array.  We can also refer to
        variables like `var1`.
    var2 : int
        The type above can either refer to an actual Python type
        (e.g. ``int``), or describe the type of the variable in more
        detail, e.g. ``(N,) ndarray`` or ``array_like``.
    long_var_name : {'hi', 'ho'}, optional
        Choices in brackets, default first when optional.

    Returns
    -------
    type
        Explanation of anonymous return value of type ``type``.
    describe : type
        Explanation of return value named `describe`.
    out : type
        Explanation of `out`.

    Other Parameters
    ----------------
    only_seldom_used_keywords : type
        Explanation
    common_parameters_listed_above : type
        Explanation

    Raises
    ------
    BadException
        Because you shouldn't have done that.

    See Also
    --------
    otherfunc : relationship (optional)
    newfunc : Relationship (optional), which could be fairly long, in which
              case the line wraps here.
    thirdfunc, fourthfunc, fifthfunc

    Notes
    -----
    Notes about the implementation algorithm (if needed).

    This can have multiple paragraphs.

    You may include some math:

    .. math:: X(e^{j\omega } ) = x(n)e^{ - j\omega n}

    And even use a greek symbol like :math:`omega` inline.

    References
    ----------
    Cite the relevant literature, e.g. [1]_.  You may also cite these
    references in the notes section above.

    .. [1] O. McNoleg, "The integration of GIS, remote sensing,
       expert systems and adaptive co-kriging for environmental habitat
       modelling of the Highland Haggis using object-oriented, fuzzy-logic
       and neural-network techniques," Computers & Geosciences, vol. 22,
       pp. 585-588, 1996.

    Examples
    --------
    These are written in doctest format, and should illustrate how to
    use the function.

    >>> a = [1, 2, 3]
    >>> print [x + 3 for x in a]
    [4, 5, 6]
    >>> print "a\n\nb"
    a
    b

    """

    # Extract any model specifications

    scoring = model.specs['scoring']

    # Call the data pipeline

    model = data_pipeline(model)

    # Scoring Only or Calibration

    if scoring:
        score_with_model(model)
    else:
        model = model_pipeline(model)

    # Return the completed model

    return model


#
# Function main
#

def main(args=None):
    r"""AlphaPy Data Pipeline

    Several sentences providing an extended description. Refer to
    variables using back-ticks, e.g. `var`.

    Parameters
    ----------
    var1 : array_like
        Array_like means all those objects -- lists, nested lists, etc. --
        that can be converted to an array.  We can also refer to
        variables like `var1`.
    var2 : int
        The type above can either refer to an actual Python type
        (e.g. ``int``), or describe the type of the variable in more
        detail, e.g. ``(N,) ndarray`` or ``array_like``.
    long_var_name : {'hi', 'ho'}, optional
        Choices in brackets, default first when optional.

    Returns
    -------
    type
        Explanation of anonymous return value of type ``type``.
    describe : type
        Explanation of return value named `describe`.
    out : type
        Explanation of `out`.

    Other Parameters
    ----------------
    only_seldom_used_keywords : type
        Explanation
    common_parameters_listed_above : type
        Explanation

    Raises
    ------
    BadException
        Because you shouldn't have done that.

    See Also
    --------
    otherfunc : relationship (optional)
    newfunc : Relationship (optional), which could be fairly long, in which
              case the line wraps here.
    thirdfunc, fourthfunc, fifthfunc

    Notes
    -----
    Notes about the implementation algorithm (if needed).

    This can have multiple paragraphs.

    You may include some math:

    .. math:: X(e^{j\omega } ) = x(n)e^{ - j\omega n}

    And even use a greek symbol like :math:`omega` inline.

    References
    ----------
    Cite the relevant literature, e.g. [1]_.  You may also cite these
    references in the notes section above.

    .. [1] O. McNoleg, "The integration of GIS, remote sensing,
       expert systems and adaptive co-kriging for environmental habitat
       modelling of the Highland Haggis using object-oriented, fuzzy-logic
       and neural-network techniques," Computers & Geosciences, vol. 22,
       pp. 585-588, 1996.

    Examples
    --------
    These are written in doctest format, and should illustrate how to
    use the function.

    >>> a = [1, 2, 3]
    >>> print [x + 3 for x in a]
    [4, 5, 6]
    >>> print "a\n\nb"
    a
    b

    """

    # Logging

    logging.basicConfig(format="[%(asctime)s] %(levelname)s\t%(message)s",
                        filename="alphapy.log", filemode='a', level=logging.DEBUG,
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

    parser = argparse.ArgumentParser(description="AlphaPy Parser")
    parser.add_argument("-d", dest="cfg_dir", default=".",
                        help="directory location of configuration file")
    parser.add_mutually_exclusive_group(required=False)
    parser.add_argument('--score', dest='scoring', action='store_true')
    parser.add_argument('--train', dest='scoring', action='store_false')
    parser.set_defaults(scoring=False)
    args = parser.parse_args()

    # Read configuration file

    specs = get_model_config(args.cfg_dir)
    specs['scoring'] = args.scoring

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


#
# MAIN PROGRAM
#

if __name__ == "__main__":
    main()
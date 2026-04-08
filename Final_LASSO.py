import pandas as pd
import geopandas as gpd 
import requests 
import json
from datetime import datetime
from io import StringIO
import csv
import time
import os
import airqualityandclimateAPI
import statsmodels.api as sm
import numpy as np

from statsmodels.stats.outliers_influence \
     import variance_inflation_factor as VIF
from statsmodels.stats.anova import anova_lm

from ISLP import load_data
from ISLP.models import (ModelSpec as MS,
                         summarize,
                         poly)
from linearmodels.panel import PanelOLS

from statsmodels.api import OLS
import sklearn.model_selection as skm
import sklearn.linear_model as skl

from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler
from sklearn.preprocessing import OneHotEncoder
from sklearn.impute import SimpleImputer

from sklearn.compose import make_column_selector as selector

from sklearn.pipeline import Pipeline
from group_lasso import GroupLasso
from sklearn.model_selection import GridSearchCV
from sklearn.model_selection import KFold, cross_val_score

import Analysis

######## Updated Final LASSO model: ##########

def final_LASSO(df, pm=True):
    df = df
    keepnonnumeric = ['CLIMATE_STATION_NAME', 'AQ_STATION_NAME']
    
    # Columns to drop:
    drops = ['CLIMATE_STATION_NAME','AQ_STATION_NAME', 'CLIMATE_STATION_NAME_lag1','AQ_STATION_NAME_lag1','site_address_lag1','CLIMATE_STATION_NAME_lag2',
           'AQ_STATION_NAME_lag2','site_address_lag2','CLIMATE_STATION_NAME_lag3','AQ_STATION_NAME_lag3',
           'site_address_lag3','site_address', 'LATITUDE', 'LONGITUDE', 'SOURCE','LATITUDE_lag1','LONGITUDE_lag1','SOURCE_lag1',
           'first_max_value', 'first_max_value_lag1','first_max_value_lag2', 'first_max_value_lag3', 'first_max_hour', 'first_max_hour_lag1','first_max_hour_lag2','first_max_hour_lag3', 'AQlatitude_lag1','AQlatitude_lag2',
           'AQlatitude_lag3','arithmetic_mean_lag1','arithmetic_mean_lag2','arithmetic_mean_lag3','aqi_lag1','aqi_lag2','aqi_lag3']
    
    df = df.drop(columns=drops)
    for col in df.columns:
        if col not in keepnonnumeric:
            df[col] = pd.to_numeric(df[col],errors='coerce')

    #Also need to drop our primary X variables to be used later in the OLS regression:
    xvars = ['Number', 'Capacity', 'Capacity_lag1', 'Capacity_lag2', 'Capacity_lag3', 'Number_lag1', 'Number_lag2', 'Number_lag3']
    df = df.drop(columns=xvars)

    df['DATE'] = pd.to_numeric(df['DATE']) #******Ask about best way to engineer data var for both lasso and RF
    df = df.dropna()

    if pm == True:
        y = df['arithmetic_mean']
    else:
        y = df['aqi']

    #One hot encoding the qualitative variables:

    ### Initiating X and Y train/test: #####
    X = df.drop(columns=['aqi', 'arithmetic_mean'])
    # X = X.apply(pd.to_numeric, errors='coerce')
    print(f"Non-numeric columns remaining: {X.dtypes[X.dtypes == 'object'].index.tolist()}")
    print(f"NaNs in X: {X.isna().sum().sum()}")

    print('Initiating Shuffle Split:')
    validation = skm.ShuffleSplit(n_splits=1,
                              test_size=0.2,
                              random_state=0)
    
    for train_idx, test_idx in validation.split(X):
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

    #Setting up pre-processing and cross validation:
    K = 5
    kfold = skm.KFold(K, shuffle=True,random_state=42) 
    #Initialize the scaler:
    scaler = StandardScaler(with_mean=True, with_std=True)

    #Preprocessing Steps:

    # Numerical:
    numeric_transformer = Pipeline(steps=[
    ('imputer', SimpleImputer(strategy='median'))])

    # Categorical:
    categorical_transformer = Pipeline(steps=[
    ('onehot', OneHotEncoder(handle_unknown='ignore', sparse_output=False)) ])

    preprocessor = ColumnTransformer(transformers=[
        ('num',numeric_transformer, selector(dtype_include=['int64','float64'])),
        ('cat', categorical_transformer, selector(dtype_include=['object','string']))
    ])

    lassoCV2 = skl.ElasticNetCV(n_alphas=100, l1_ratio=0.1, cv=kfold, random_state=42)
    pipeCVlasso = Pipeline(steps=[('preprocess', preprocessor),
                                  ('scaler', scaler),
                                  ('lasso', lassoCV2 )])
    
    # Fitting for lambda 
    print('Fitting Hyper Parameter Pipeline:')
    # print(X_train)

    pipeCVlasso.fit(X_train, y_train)
    tuned_lasso = pipeCVlasso.named_steps['lasso']
    lasso_alpha = tuned_lasso.alpha_
    print(f'Tuned alpha = {lasso_alpha}')

    # Fitting the trained lasso on the full data: 
    print('Testing the Tuned Lasso with Cross Validation:')
    lassotest = skl.ElasticNet(alpha=lasso_alpha, l1_ratio=1)
    pipeCVlassotest = Pipeline(steps=[('preprocess', preprocessor),
                                  ('scaler', scaler),
                                  ('lasso', lassotest)])

    # resultslasso = skm.cross_validate(pipeCVlassotest, 
    #                             X,
    #                             y,
    #                             cv=kfold,
    #                             scoring='neg_mean_squared_error',
    #                             return_estimator=True)

    
    resultslasso = pipeCVlassotest.fit(X, y)
    print('results saved')

    # Getting Results:
    lassoresults = resultslasso.named_steps['lasso']

    feature_names = [
    name.split('__')[-1] 
    for name in pipeCVlassotest.named_steps['preprocess'].get_feature_names_out()
    ]
    # Non Zero Lasso Regression Coefficients:
    feature_names_clean = [f for f in feature_names if f not in ['const', 'remainder__const', 'x0']]
    coef_array = lassoresults.coef_.flatten()

    coef_df = pd.DataFrame({
        'feature': feature_names_clean,
        'coefficient': coef_array
    })

    # This uses the names the model actually "saw" during fit:
    nonzerocoefs = coef_df[coef_df['coefficient'] != 0].sort_values(by='coefficient', key=abs, ascending=False)

    print(f"The non-zero coefficient estimates are:")
    print(nonzerocoefs)

    toptwenty = nonzerocoefs.head(20)['feature'].tolist()

    return coef_df, nonzerocoefs, toptwenty


    # Getting Results: 
    # lasso_rmse = np.sqrt(-resultslasso['test_score'].mean())
    # print(f"Mean CV RMSE: {lasso_rmse:.4f}")

    # # --- Coefficients across folds ---
    # fold_coefs = []
    # for estimator in resultslasso['estimator']:
    #     coef_array = estimator.named_steps['lasso'].coef_
    #     fold_coefs.append(dict(zip(X.columns, coef_array)))

    # coef_df = pd.DataFrame(fold_coefs)
    # coef_df.index = [f'Fold {i+1}' for i in range(K)]

    # nonzero_cols = coef_df.columns[(coef_df != 0).any(axis=0)]
    # print(f"\nNon-zero coefficients: {len(nonzero_cols)}")
    # print("\n--- Mean coefficient across folds (nonzero in at least one fold) ---")
    # print(coef_df[nonzero_cols].mean().sort_values(ascending=False).round(6))

    # # Getting the top 20 most important variables based on absolute value of mean coefficient across folds:
    # nonzerocoefs = coef_df[nonzero_cols].mean().sort_values(ascending=False).round(6)

    # #Getting the most important variables based on absolute value of mean coefficient across folds:
    # absvaluecoefs = nonzerocoefs.abs().sort_values(ascending=False)
    # toptwenty = absvaluecoefs.head(20).index.tolist()

    # return resultslasso, coef_df, lasso_rmse, nonzerocoefs, toptwenty








if __name__ == '__main__':

    total = Analysis.totaldata()
    print('Initiating LASSO...')
    finalLASSO = final_LASSO(total, pm=True)
    print('Complete')

    print('---------Top Features----------')
    topvars = finalLASSO[4]
    # topvars.pop(3)
    usablevars = [var for var in topvars if var != 'AQ_STATION_NAME']

    print(usablevars)
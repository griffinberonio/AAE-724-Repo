import pandas as pd
from datetime import datetime
from io import StringIO
import csv
import time
import os

#Other project Scripts:
import airqualityandclimateAPI
import Analysis


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
from sklearn.compose import make_column_selector as selector
from sklearn.impute import SimpleImputer


from sklearn.pipeline import Pipeline
from group_lasso import GroupLasso
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import GridSearchCV
from sklearn.model_selection import KFold, cross_val_score
from sklearn.model_selection import train_test_split

def random_forest(df, pm = True):
    df = df
    keepnonnumeric = ['CLIMATE_STATION_NAME', 'AQ_STATION_NAME']
    # keepnonnumeric = ['CLIMATE_STATION_NAME']
    
    # Columns to drop:
    drops = ['CLIMATE_STATION_NAME_lag1','AQ_STATION_NAME_lag1','site_address_lag1','CLIMATE_STATION_NAME_lag2',
           'AQ_STATION_NAME_lag2','site_address_lag2','CLIMATE_STATION_NAME_lag3','AQ_STATION_NAME_lag3',
           'site_address_lag3','site_address', 'LATITUDE', 'LONGITUDE', 'SOURCE','LATITUDE_lag1','LONGITUDE_lag1','SOURCE_lag1',
           'first_max_value', 'first_max_value_lag1','first_max_value_lag2', 'first_max_value_lag3','AQlatitude_lag1','AQlatitude_lag2',
           'AQlatitude_lag3','arithmetic_mean_lag1','arithmetic_mean_lag2','arithmetic_mean_lag3','aqi_lag1','aqi_lag2','aqi_lag3']
    
    df = df.drop(columns=drops)
    for col in df.columns:
        if col not in keepnonnumeric:
            df[col] = pd.to_numeric(df[col],errors='coerce')

    # df['DATE'] = pd.to_numeric(df['DATE']) #****** Ask about best way to engineer data var for both lasso and RF
    df = df.dropna()

    if pm == True:
        y = df['arithmetic_mean']
    else:
        y = df['aqi']      

    X = df.drop(columns=['aqi', 'arithmetic_mean'])

    #Setting up pre-processing and cross validation:
    K = 5
    kfold = skm.KFold(K, shuffle=True,random_state=42) 

    #Initialize the scaler:
    scaler = StandardScaler(with_mean=True, with_std=True)

    # print(X.head())
    print(f"Number of NaNs in X: {X.isna().sum().sum()}")

    numeric_transformer = Pipeline(steps=[
    ('imputer', SimpleImputer(strategy='median'))])

    categorical_transformer = Pipeline(steps=[
    ('onehot', OneHotEncoder(handle_unknown='ignore', sparse_output=False))
    ])

    # Combine numeric + categorical
    preprocessor = ColumnTransformer(
        transformers=[
            ('num', numeric_transformer, selector(dtype_include=['int64', 'float64'])),
            ('cat', categorical_transformer, selector(dtype_include=['object','string']))
        ])
    
    print('Preprocessing setup complete.')

     #Train test split:
    x_train, x_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=0) 

    ############################
    # Tuning RF hyperparams:
    ############################

    #Grid Search: 

    #Actual Training Params:
    param_grid = {
    'bootstrap': [True],
    'max_depth': [80, 90, 100, 110],
    'max_features': [2, 3],
    'min_samples_leaf': [2, 3, 4, 5],
    'min_samples_split': [8, 10, 12],
    'n_estimators': [100, 200, 300, 400]}

    # Debugging training params:
    param_grid_test = {
    'bootstrap': [True],
    'max_depth': [80],
    'max_features': [2, ],
    'min_samples_leaf': [2],
    'min_samples_split': [8],
    'n_estimators': [100]}

    grid_search = Pipeline(steps=[('preprocessing', preprocessor),
                                  ('Grid Search', GridSearchCV(estimator=RandomForestRegressor(random_state=42),
                                                               param_grid=param_grid_test, #Using the debugging params
                                                              # param_grid=param_grid, #Using the actual training params
                                                               cv=kfold,
                                                               scoring = "neg_mean_squared_error"),
                                                               )])

    print('Fitting the Grid Search for RF hyperparameter tuning...')
    grid_search.fit(x_train, y_train)

    #Retrieving the best hyperparameters:
    bestestimators = grid_search.named_steps['Grid Search'].best_params_['n_estimators']
    bestmaxdepth = grid_search.named_steps['Grid Search'].best_params_['max_depth']
    bestmaxfeatures = grid_search.named_steps['Grid Search'].best_params_['max_features']
    bestminleaf = grid_search.named_steps['Grid Search'].best_params_['min_samples_leaf']
    bestminsplit = grid_search.named_steps['Grid Search'].best_params_['min_samples_split']

    print(bestestimators)

    #Defining the RF model pipeline:
    rf_pipeline = Pipeline(steps=[
    ('preprocess', preprocessor),
    ('model', RandomForestRegressor(
        n_estimators=bestestimators,
        max_depth=bestmaxdepth,
        max_features=bestmaxfeatures,
        min_samples_leaf=bestminleaf,
        min_samples_split=bestminsplit,
        random_state=42,
        n_jobs=-1,
    ))])

    ############################
    # Tuning RF hyperparams:
    ############################
    print('Fitting the RF model')
    print(x_train.shape)
    rf_pipeline.fit(x_train, y_train)

    n_scores = cross_val_score(rf_pipeline, x_train, y_train,
                           cv=KFold(n_splits=5, shuffle=True, random_state=42),
                           scoring = "neg_mean_squared_error").mean()

    prediction = rf_pipeline.predict(x_test)

    ################### Retreiving feature importances: ###########################:

    feature_names = rf_pipeline.named_steps['preprocess'].get_feature_names_out()
    rf_model = rf_pipeline.named_steps['model']
    importances = rf_model.feature_importances_

    feature_names = [f.replace('num__','') for f in feature_names]

    # Combine into a DataFrame:
    feat_imp = pd.DataFrame({
        'feature': feature_names,
        'importance': importances
    }).sort_values(by='importance', ascending=False)

    print(feat_imp.head(40))

    print(n_scores)
    print(prediction)

    return rf_pipeline, n_scores, prediction, feat_imp

    

# Panel OLS using resulting variables:



    





if __name__ == "__main__":

    dependent_vars = ['arithmetic_mean','first_max_value']
    # cleaning_total_data(totaldf,dependent_vars)

    # Variables:
    xclimate = ['DailyAverageDryBulbTemperature', 'DailyAverageWindSpeed','DailyMaximumDryBulbTemperature',
       'DailyMinimumDryBulbTemperature', 'DailyPeakWindSpeed',
       'DailyPrecipitation','DailySustainedWindSpeed', 'DailySustainedWindDirection_sin', 'DailySustainedWindDirection_cos',
       'DailyAveragePrecipitation', 'DailyAveragePressureChange',
       'DailyAverageRelativeHumidity',]

    y = ['arithmetic_mean']
    yaqi = ['aqi']

    fe = ['CLIMATE_STATION_NAME','YEAR']

    xenergy= ['DailyAverageDryBulbTemperature', 'DailyAverageWindSpeed',
        'DailyDepartureFromNormalAverageTemperature',
        'DailyMaximumDryBulbTemperature',
       'DailyMinimumDryBulbTemperature', 'DailyPeakWindSpeed',
       'DailyPrecipitation',
       'DailySustainedWindSpeed',
       'DailyPeakWindDirection_sin', 'DailyPeakWindDirection_cos',
       'DailySustainedWindDirection_sin', 'DailySustainedWindDirection_cos',
       'DailyAverageDewPointTemperature',
       'DailyAveragePrecipitation', 'DailyAveragePressureChange',
       'DailyAverageRelativeHumidity', 'DailyAverageSeaLevelPressure',
       'DailyAverageStationPressure', 'DailyAverageWetBulbTemperature',
       'DailyAverageWindGustSpeed', 'DailyAverageWindDirection_sin',
       'DailyAverageWindDirection_cos']
    
    yenergy = ['Demand']
    feenergy = ['CLIMATE_STATION_NAME','MONTH']

    # Calling data:
    total = Analysis.totaldata()
    # print(total.head())

    random_forest(total, pm=True)


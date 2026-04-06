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

from sklearn.pipeline import Pipeline
from group_lasso import GroupLasso
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import GridSearchCV
from sklearn.model_selection import KFold, cross_val_score

def random_forest(df, pm=True):
    df = df
    keepnonnumeric = ['CLIMATE_STATION_NAME', #Columns to keep in the df but are nonnumeric
    'AQ_STATION_NAME']
    
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

    categorical_transformer = Pipeline(steps=[
    ('onehot', OneHotEncoder(handle_unknown='ignore', sparse_output=False))
    ])

    # Combine numeric + categorical
    preprocessor = ColumnTransformer(
        transformers=[
            ('cat', categorical_transformer, selector(dtype_include=['object','string']))
        ])
    
    print('Preprocessing setup complete.')

    #Defining the RF model pipeline:
    rf_pipeline = Pipeline(steps=[
    ('preprocess', preprocessor),
    ('model', RandomForestRegressor(
        n_estimators=50,
        random_state=42,
        n_jobs=-1
    ))])

    print('Fitting the RF model')
    

    

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


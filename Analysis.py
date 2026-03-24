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
from sklearn.pipeline import Pipeline
from group_lasso import GroupLasso
from sklearn.model_selection import GridSearchCV
from sklearn.model_selection import KFold, cross_val_score

import pyhdfe


################### Downloading Data ##################################
#climate data:
climatedatapath = f"/Users/griffinberonio/Documents/AAE 724/Datasets/climatedata/totalclimatedata.csv"
climatedata = pd.read_csv(climatedatapath)

#Air Quality Data:
airqualitydatapath = f'/Users/griffinberonio/Documents/AAE 724/Datasets/master_aqs_df_17_031.csv'
airqualitydata = pd.read_csv(airqualitydatapath)

#Renewable Energy Data: 
renewablespath = '/Users/griffinberonio/Documents/AAE 724/Datasets/CookCountyRenewablesData.csv'
renewablesdata = pd.read_csv(renewablespath, encoding='latin-1')

#Daily Emissions Data:
emissionspath = f'/Users/griffinberonio/Documents/AAE 724/Datasets/IL_Daily_Emissions.csv'
emissiondata = pd.read_csv(emissionspath)

#Daily Energy Demand:
energydemandpath = f'/Users/griffinberonio/Documents/AAE 724/Datasets/Energy_Demand_CHIPJM.csv'
energydemanddata = pd.read_csv(energydemandpath)

#Traffic Data:
trafficdatapath = '/Users/griffinberonio/Documents/AAE 724/Datasets/DailyTrafficData_Chicago.csv'

#Total Data From Notebook:
totaldatapath = '/Users/griffinberonio/Documents/AAE 724/Datasets/totaldata.csv'
totaldf = pd.read_csv(totaldatapath)

#Data used to run the exploratory Panel OLS models from the first stage of the analysis: 
def firstmodelstotaldata():
    totaldatapath = '/Users/griffinberonio/Documents/AAE 724/Datasets/totaldata.csv'
    totaldf = pd.read_csv(totaldatapath)
    totaldf['DATE'] = pd.to_datetime(totaldf['DATE'])
    totaldf['DailyPrecipitation'] = totaldf['DailyPrecipitation'].replace('T',0)
    totaldf['DailyPrecipitation'] = totaldf['DailyPrecipitation'].astype(float)
    totaldf['YEAR'] = totaldf['DATE'].dt.year

    return totaldf


#Cleaned data for the second stage of the analysis: 
def totaldata(include_demand=False):

    totaldatapath = '/Users/griffinberonio/Documents/AAE 724/Datasets/totaldata.csv'
    totaldf = pd.read_csv(totaldatapath)
    totaldf['DATE'] = pd.to_datetime(totaldf['DATE'])
    totaldf['DailyPrecipitation'] = totaldf['DailyPrecipitation'].replace('T',0)
    totaldf['DailyPrecipitation'] = totaldf['DailyPrecipitation'].astype(float)
    totaldf['YEAR'] = totaldf['DATE'].dt.year
    totaldf['sunrise_sin'] = np.sin(2*np.pi * totaldf['Sunrise']/86400)
    totaldf['sunrise_cos'] = np.cos(2*np.pi * totaldf['Sunrise']/86400)
    totaldf['sunset_sin'] = np.sin(2*np.pi * totaldf['Sunset']/86400)
    totaldf['sunset_cos'] = np.cos(2*np.pi * totaldf['Sunset']/86400)
    #Lagging variables:
    problematic_cols = []
    if include_demand == True:
        problematic_cols = ['DailyHeatingDegreeDays','DailyCoolingDegreeDays','DailySnowDepth','DailySnowfall','DailyWeather',
                            'validity_indicator',] #These columns are dropped due to large amounts of missing data 
    else:
        problematic_cols = ['DailyHeatingDegreeDays','DailyCoolingDegreeDays','validity_indicator','DailySnowDepth','DailySnowfall','DailyWeather','Demand']

    totaldf = totaldf.drop(columns=problematic_cols)
    totaldf = totaldf.dropna()
    lag_1 = totaldf.shift(1).add_suffix('_lag1')
    lag_2 = totaldf.shift(2).add_suffix('_lag2')
    lag_3 = totaldf.shift(3).add_suffix('_lag3')
    finaldropcols = []


    df_final = totaldf.join([lag_1,lag_2,lag_3],how='inner')
    laggedcols = [col for col in df_final.columns if 'lag' in col]

    df_final = df_final.drop_duplicates()
    return df_final

def cleaning_total_data(df,variables):
    dependent_vars = ['aqi','arithmetic_mean','first_max_value']
    needed_vars = variables 

    num_missing = {}
    for col in variables:
        num_missing[col] = df[col].isna().sum()

    # print(df.shape)
    print(num_missing)
    tempdf = df.dropna(subset=variables)
    print(tempdf.head())

    return tempdf

# come back to this:
class totaldataclass:
    def __init__(self, matrixname, columns=[]):
        data = totaldf
        self.name = matrixname
        self.matrix = data[columns]

#Model 1:
# Model1: Regressing PM 2.5 on a matrix of climate variables alone:

def model_1(data, x, y, fe):
    df = data
    xmatrix = x
    totalcols = xmatrix + y + fe
    # print(totalcols)

    df = df[totalcols]
    df['DATE'] = pd.to_datetime(df['DATE'])
    clusters = df['CLIMATE_STATION_NAME']

    # df['YEAR'] = df['DATE'].dt.year.astype(str)
    df['YEAR'] = pd.to_numeric(df['DATE'].dt.year)

    df = df.dropna(subset=totalcols)

    # df_with_dummies = pd.get_dummies(
    #     df, 
    #     columns=['CLIMATE_STATION_NAME','YEAR'], 
    #     drop_first=True
    # )
    df_with_dummies = pd.get_dummies(
        df,
        columns=['CLIMATE_STATION_NAME','YEAR'],
        drop_first=True
        )
    
    cols = df_with_dummies.columns

    for col in cols:
        if col != 'CLIMATE_STATION_NAME_CHICAGO PALWAUKEE AIRPORT, IL US':
            df_with_dummies[col] = pd.to_numeric(df_with_dummies[col], errors='coerce')
    df_with_dummies = df_with_dummies.dropna()

    Y = df_with_dummies['arithmetic_mean'] 
    X = df_with_dummies.drop(columns=['arithmetic_mean','DATE'])
    
    X_final = sm.add_constant(X)

    
    ols_model = sm.OLS(Y, X_final.astype(float))

    results = ols_model.fit(cov_type='cluster', cov_kwds={'groups': clusters.loc[df_with_dummies.index]})
    summary = summarize(results)
    summary2 = pd.DataFrame(summary).reset_index()

    print(summary2)

    return summary2
    

#Panel Two Way Fixed Effects Model with Date and Station-based fixed effects: 


def model_1_panel(df, x, y, fe):
    df['DATE'] = pd.to_datetime(df['DATE'])
    # df['YEAR'] = df['DATE'].dt.year
    totalcols = x + y + fe
    df = df[totalcols]

    # Convert all predictors and Y to numeric
    for col in x + y:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # Drop rows with any missing values
    model_df = df.dropna()

    # Set MultiIndex
    df_panel = df.set_index(['CLIMATE_STATION_NAME', 'YEAR'])

    # Define X and Y
    Y = df_panel[y[0]]  # assuming y = ['arithmetic_mean']
    X = df_panel[x]

    # Fit the model
    model = PanelOLS(
        Y,
        X,
        entity_effects=True,
        time_effects=True
    )

    results = model.fit(cov_type='clustered', cluster_entity=True)
    print(results)

    return results


def model_2_aqi(data, x, y, fe):

    df = data
    df['DATE'] = pd.to_datetime(df['DATE'])
    df['YEAR'] = df['DATE'].dt.year
    totalcols = x + y + fe
    df = df[totalcols]

    # Convert all predictors and Y to numeric
    for col in x + y:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # Drop rows with any missing values
    model_df = df.dropna()
    print(model_df.head())
    # Set MultiIndex
    df_panel = model_df.set_index(fe)

    # Define X and Y
    Y = df_panel[y[0]]  # assuming y = ['aqi']
    X = df_panel[x]

    # Fit the model
    model = PanelOLS(
        Y,
        X,
        entity_effects=True,
        time_effects=True
    )

    results = model.fit(cov_type='clustered', cluster_entity=True)
    print(results)

    return results


# Model 3: Regressing Energy demand on climate variables: 
# Rexamine which variables are included, add a few more 
# Include Seasonal column (4 categories, broken up by season based on month)
def model_3_energy_climate(data, x, y, fe):
    df = data
    df['DATE'] = pd.to_datetime(df['DATE'])
    df['MONTH'] = df['DATE'].dt.month
    df['YEAR'] = df['DATE'].dt.year
    # df['MONTH'] = df['MONTH'].astype('category')
    # seasons = {
    #     '12':'1','1':'1','2':'1',  #winter
    #      '3':'2','4':'2','5':'1',  #Spring
    #      '6':'3','7':'3','8':'3',  #Summer
    #      '9':'4','10':'4','11':'4' #Fall
    # }
    # df['month'] = df['MONTH'].astype(str)
    # df['SEASON'] = df['month'].map(seasons)
    # df['SEASON'] = df['SEASON'].astype('category')
    # df = df.drop(columns='month')
    # x.append('SEASON')

    totalcols = x+y+fe

    for col in x + y:
        df[col] = pd.to_numeric(df[col],errors='coerce')

    df = df[totalcols]
    model_df = df.dropna()

    # print(model_df.head())

    df_panel = model_df.set_index(fe)

    Y = df_panel[y[0]] 
    X = df_panel[x]

    # Fit the model
    model = PanelOLS(
        Y,
        X,
        entity_effects=True,
        time_effects=True
    )

    results = model.fit(cov_type='clustered', cluster_entity=True)
    print(results)

    return results


############################################## Lasso ##############################################################################

######################################################################################################################################

def LASSOsetup(data, pm_mean = True):
    df = data
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

    df['DATE'] = pd.to_numeric(df['DATE'])
    df = df.dropna()

    if pm_mean == True:
        y = df['arithmetic_mean'].values

    else:
        y = df['aqi'].values

    #Dropping y vars:
    df = df.drop(columns = ['aqi','arithmetic_mean'])
    df = df.drop(columns='AQ_STATION_NAME') # Use this when not grouping by AQ_STATION_NAME. 

    #Making dummy variables:

    climate_dummies = pd.get_dummies(df['CLIMATE_STATION_NAME'])
    # aq_dummies = pd.get_dummies(df['AQ_STATION_NAME'])
    year_dummies = pd.get_dummies(df['YEAR'])

    # nonstations = df.drop(columns=['CLIMATE_STATION_NAME', 'AQ_STATION_NAME','YEAR'])
    nonstations = df.drop(columns=['CLIMATE_STATION_NAME','YEAR']) # Use this when not grouping by AQ_STATION_NAME

    # Separating out renewable variables:
    renewable_cols = []
    for col in df.columns:
        if ('Number' in col) | ('Capacity' in col):
            renewable_cols.append(col)
    
    # Groups for group LASSO:
    groups = []
    current_group = 0

    # Group 0 to N: Individual climate variables (each gets its own ID)

    #Syntax for creating a renweables group:

    # for var in range(len(nonstations.columns)):
    #     if nonstations.columns[var] in renewable_cols:
    #         groups.append(current_group)
    #     else:
    #         groups.append(current_group)
    #     current_group += 1

    for var in range(len(nonstations.columns)):
        groups.append(current_group)
        current_group += 1

    # Group N+1: All Climate Station dummies share one ID
    groups.extend([current_group] * climate_dummies.shape[1])
    current_group += 1

    # Group N+2: All Year dummies share one ID
    groups.extend([current_group] * year_dummies.shape[1])

    #Group N+3: All Air Quality Stations share one ID:
    # groups.extend([current_group] * aq_dummies.shape[1])
    # current_group += 1

    groups = np.array(groups)


    x_vars = nonstations.columns 
    # X = pd.concat([df[x_vars], climate_dummies, aq_dummies, year_dummies], axis=1)
    X = pd.concat([df[x_vars], climate_dummies, year_dummies], axis=1)


    X.columns = X.columns.astype(str)

    continuous_indices = [X.columns.get_loc(c) for c in x_vars]
    dummy_indices = [X.columns.get_loc(c) for c in X.columns if c not in x_vars]

    print(f"X columns: {X.shape[1]}")
    print(f"Groups length: {len(groups)}")

    if X.shape[1] != len(groups):
        print("❌ STILL A MISMATCH!")
    else:
        print("✅ MATCHED!")

    #Initialize 5 fold K-fold cross validation algorithm
    K = 5
    kfold = skm.KFold(K,
                  shuffle=True,
                  random_state=42) 


    #Initialize the scaler:
    scaler = StandardScaler(with_mean=True, with_std=True)

    #Preprocessor separates continuous numerical variables from dummy variables based on indices:
    preprocessor = ColumnTransformer(
    transformers=[
        ('num', scaler, continuous_indices),
        ('pass', 'passthrough', dummy_indices) 
    ])     

    # Pipeline:
    print('Initializing pipeline')

    renewable_indices = [i for i, col in enumerate(nonstations.columns) if col in renewable_cols]

    # Build weight array: 1.0 for all groups, 0.0 for renewable groups
    n_groups = current_group  
    group_weights = np.ones(n_groups)
    for idx in renewable_indices:
        group_weights[idx] = 0.0  # Makes sure the renewable variables are exempted. 

    pipe = Pipeline(steps=[
    ('preprocessor', preprocessor),
    ('group_lasso', GroupLasso(
        groups=groups, 
        l1_reg=0.05, 
        group_reg=0.1, 
        fit_intercept=True,
        supress_warning=True))
    ])

    print('Setup complete')

    param_grid = {
    'group_lasso__l1_reg': [0.001, 0.01, 0.1, 1.0],
    'group_lasso__group_reg': [0.01, 0.1, 0.5]
    }

    grid = GridSearchCV(pipe, param_grid, cv=kfold, scoring='neg_mean_squared_error')

    # Fitting the gridsearch and cross validation:
    print('Fitting Gridsearch...')
    start = time.time()
    grid.fit(X, y)

    cv_rmse = np.sqrt(-grid.best_score_)
    print(f"Best Cross-Validated RMSE: {cv_rmse:.4f}")
    # print(f"Best R2: {grid.best_score_}")
    print(f"Best Params: {grid.best_params_}")
    end = time.time()
    print(f'Grid search took: {end-start}')

    ########### Getting the CV MSE: ################

    best_neg_mse = grid.best_score_
    best_mse = -best_neg_mse

    print(f"Best Cross-Validated MSE: {best_mse:.4f}")
    print(f"Best RMSE (Root MSE): {np.sqrt(best_mse):.4f}")

    ########### Getting the Coefficients ###########
    best_pipe = grid.best_estimator_

    # Reach into the winner to get the coefficients
    best_lasso = best_pipe.named_steps['group_lasso']
    coefs = best_lasso.coef_

    #Getting the corresponding feature names:
    preprocessor = best_pipe.named_steps['preprocessor']
    feature_names = preprocessor.get_feature_names_out()
    feature_names_clean = np.array([name.split('__')[-1] for name in feature_names])

    coef_array = np.array(coefs).flatten()

    nonzero_mask = coef_array != 0
    nonzero_coefs = coef_array[nonzero_mask]
    nonzero_features = feature_names_clean[nonzero_mask]

    print(f"Number of non-zero coefficients: {len(nonzero_coefs)}")
    print("\n{:<40} {:>15}".format("Feature", "Coefficient"))
    print("-" * 57)
    for feat, coef in zip(nonzero_features, nonzero_coefs):
        print("{:<40} {:>15.6f}".format(feat, coef))


########################################
# Simplified LASSO: 
########################################

def FWLasso(df, pm = True):
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

    df['DATE'] = pd.to_numeric(df['DATE'])
    df = df.dropna()

    if pm == True:
        y = df['arithmetic_mean']
    else:
        y = df['aqi']

    # df = df.drop(columns = ['aqi','arithmetic_mean'])
    # df = df.drop(columns='AQ_STATION_NAME')

    X = df.drop(columns=['aqi', 'arithmetic_mean', 'AQ_STATION_NAME', 'CLIMATE_STATION_NAME', 'YEAR'])
    X = X.apply(pd.to_numeric, errors='coerce')
    print(f"Non-numeric columns remaining: {X.dtypes[X.dtypes == 'object'].index.tolist()}")
    print(f"NaNs in X: {X.isna().sum().sum()}")

    #These become the new X and Y:
    algorithm = pyhdfe.create(df[['CLIMATE_STATION_NAME', 'YEAR']].values)
    y_resid = algorithm.residualize(y.values.reshape(-1, 1)).flatten()
    X_resid = algorithm.residualize(X.values)
    X_resid = pd.DataFrame(X_resid, columns=X.columns)

    validation = skm.ShuffleSplit(n_splits=1,
                              test_size=0.2,
                              random_state=0)

    for train_idx, test_idx in validation.split(X_resid):
        X_train, X_test = X_resid.iloc[train_idx], X_resid.iloc[test_idx]
        y_train, y_test = y_resid[train_idx], y_resid[test_idx]

    #Setting up pre-processing and cross validation:
    K = 5
    kfold = skm.KFold(K, shuffle=True,random_state=42) 
    #Initialize the scaler:
    scaler = StandardScaler(with_mean=True, with_std=True)

    lassoCV2 = skl.ElasticNetCV(n_alphas=100, l1_ratio=0.1, cv=kfold)
    pipeCVlasso = Pipeline(steps=[('scaler', scaler),
                         ('lasso', lassoCV2)])
    
    pipeCVlasso.fit(X_train, y_train)
    tuned_lasso = pipeCVlasso.named_steps['lasso']
    lasso_alpha = tuned_lasso.alpha_
    print(f'Tuned alpha = {lasso_alpha}')

    # Testing the tuned lasso on the test data: 
    lassotest = skl.ElasticNet(alpha=lasso_alpha, l1_ratio=1)
    pipeCVlassotest = Pipeline(steps=[('scaler', scaler), ('lasso', lassotest)])

    resultslasso = skm.cross_validate(pipeCVlassotest, 
                                X_resid,
                                y_resid,
                                cv=kfold,
                                scoring='neg_mean_squared_error',
                                return_estimator=True ) #outer cross-validation to evaluate the entire process

    # Average Lasso MSE across all folds:
    lasso_rmse = np.sqrt(-resultslasso['test_score'].mean())
    print(f"Mean CV RMSE: {lasso_rmse:.4f}")

    # --- Coefficients across folds ---
    fold_coefs = []
    for estimator in resultslasso['estimator']:
        coef_array = estimator.named_steps['lasso'].coef_
        fold_coefs.append(dict(zip(X_resid.columns, coef_array)))

    coef_df = pd.DataFrame(fold_coefs)
    coef_df.index = [f'Fold {i+1}' for i in range(K)]

    nonzero_cols = coef_df.columns[(coef_df != 0).any(axis=0)]
    print(f"\nNon-zero coefficients: {len(nonzero_cols)}")
    print("\n--- Mean coefficient across folds (nonzero in at least one fold) ---")
    print(coef_df[nonzero_cols].mean().sort_values(ascending=False).round(6))

    return resultslasso, coef_df, lasso_rmse




    


    


# Model 4: Fossil fuel generation output (MWh) based on above metrics ^
# Model 5: Regressing Pm2.5/ aqi on renewables, controlling. for climate metrics 
#Model 6-7: adding all the things together. 

########################################################################################################
if __name__ == '__main__':

    total = totaldata()

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

    # model_1(totaldf, xclimate, y, fe)
    # model_1_panel(total, xenergy, y, fe)

    # model_2_aqi(totaldata(), xclimate, yaqi, fe)

    

    #Energy Demand: 
    # model_3_energy_climate(total, xenergy, yenergy, feenergy)

    #Fossil Fuel Dispatch Output Generation: 
    yfossil = ['Gross Load (MWh)']

    # model_3_energy_climate(total,xenergy,yfossil, feenergy)

    #PM mean on renewables and capacity controlling for climate with year and station FE:
    xenergyandrenewables = xenergy + ['Number', 'Capacity']
    
    # model_3_energy_climate(total, xenergyandrenewables, y,fe)

    # AQI on renewables and capacity controlling for climate with year and station FE:
    # model_3_energy_climate(total,xenergyandrenewables,yaqi,fe)

    #######################LASSO#########################

    # LASSOsetup(total)

    FWLasso(total)





   



library(dplyr)
library(ggplot2)
library(tidyverse)
library(tigris)
library(sf)
library(lubridate)

setwd('/Users/griffinberonio/Documents/AAE 724/AAE-724-Repo')

# Renewable Generators Dataset:
renewable_generators <- read.csv('/Users/griffinberonio/Documents/AAE 724/Datasets/RenewableGeneratorsRegisteredinGATS_20260203_110659.csv')
renewable_generators %>% head(10)


#Filtering to only include data from Cook County, Illinois:
ILgens <- renewable_generators %>% filter(County =='Cook' & State == 'IL') %>% select(c(Plant.Name,
                                                                                        Unit.Name,
                                                                                        GATS.Unit.ID,
                                                                                      
                                                                                        Nameplate,
                                                                                        Date.Online,
                                                                                        Primary.Fuel.Type
                                                                                        ))

ILgens <- ILgens %>% mutate("Date.Online" = mdy(Date.Online)) %>% 
  mutate('YEAR' = year(Date.Online))
ILgens %>% dim()
ILgens %>% head()

# Alternative solar gens data by census tract:
  # from the Illinois Solar Map 
solar_data <- read.csv('/Users/griffinberonio/Documents/AAE 724/Solar_projects_solarmap.csv')
solar_data %>% dim()
solar_data <- solar_data %>% mutate('DATE' = as_datetime(energization_date)) %>% 
  mutate('YEAR' = year(DATE))
solar_data %>% head()

solar_data$county %>% unique()
cook_solar <- solar_data %>% filter(county== 31)
cook_solar <- cook_solar %>% rename('GEOID' = census_tract)
cook_solar %>% head()




# Joining Solar Plants to Census tracts: -----------------------------------------
tracts = tracts(state='IL', county = 'Cook')
tracts %>% summarize('AWATER') 


tracts %>% head()

tractsandsolar <- tracts %>% st_join(tracts, cook_solar)

# Mapping Plant IDs for Time Period 1: ------------------------------------

#County area Basemap: 

cook <- "Cook"
  
il_counties <- counties(state = "IL", cb = TRUE, class = "sf")
il_counties$NAME
# il_counties %>% head(0)
il_counties <- il_counties %>%
  rename('COUNTY' = NAME)
il_counties %>% select(COUNTY)
il_counties %>% colnames
cook_county <- il_counties %>% filter(COUNTY == cook) %>% 
  select(COUNTY)
cook_county 
il_counties %>% colnames()

ggplot() +
  geom_sf(data=cook_county, color = 'black') +
  geom_sf(data=tracts, color='black')+
  # scale_fill_gradient(low='lightblue', high='darkmagenta', na.value = 'grey90') +
  theme_minimal() +
  labs(title = "Cook County")


# Mapping Plant IDs for Time Period 2: ------------------------------------

# Mapping Plant IDs for Time Period 3: ------------------------------------









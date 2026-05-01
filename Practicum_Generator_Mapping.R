

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

  #Deleting large lake tract by area
tracts <- tracts %>% mutate('AREA' = as.numeric(st_area(tracts)))
maxarea <- max(tracts$AREA)
tractsclean <- tracts %>% subset(AREA < maxarea)
tractsclean %>% head()


cook_solar %>% colnames()
cook_solar$category %>% unique()

tractsandsolar <- tractsclean %>% inner_join(cook_solar, by='GEOID')
tractsandsolar <- tractsandsolar %>% drop_na(YEAR)
minyear <- min(tractsandsolar$YEAR)
maxyear <- max(tractsandsolar$YEAR)
minyear
maxyear

tractsandsolar %>% head()
tractsandsolar %>%
  st_drop_geometry() %>%
  count(GEOID) %>%
  summary()

# County area Basemap: 
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

# Multiple DFs per year snapshot:

#2019
year2019 <- tractsandsolar %>% filter(YEAR == 2019)
year2019 %>% dim()
gencounts2019 <- year2019 %>% 
  group_by(GEOID,geometry) %>% 
  summarize('GENCOUNTS' = n(), .groups = 'drop') %>% 
  st_as_sf() %>% 
  mutate(YEAR = 2019)

#2022
year2022 <- tractsandsolar %>% filter(YEAR == 2022)
year2022 %>% dim()
gencounts2022 <- year2022 %>% 
  group_by(GEOID,geometry) %>% 
  summarize('GENCOUNTS' = n(), .groups = 'drop') %>% 
  st_as_sf() %>% 
  mutate(YEAR = 2022)

#2025
year2025 <- tractsandsolar %>% filter(YEAR == 2025)
year2025 %>% dim()
gencounts2025 <- year2025 %>% 
  group_by(GEOID,geometry) %>% 
  summarize('GENCOUNTS' = n(), .groups = 'drop') %>% 
  st_as_sf() %>% 
  mutate(YEAR = 2025)

# --- 2. Get shared min/max across all three years ---
all_counts <- c(gencounts2019$GENCOUNTS, gencounts2022$GENCOUNTS, gencounts2025$GENCOUNTS)
scale_min <- min(all_counts, na.rm = TRUE)
scale_max <- max(all_counts, na.rm = TRUE)

# Mapping Generators for all years with a function: ------------------------------------
map_year <- 'none'
map_year <- function(df, year) {
  ggplot(df) +
    geom_sf(data=cook_county, color = 'black') +
    geom_sf(data=tractsclean, color='black')+
    geom_sf(aes(fill = GENCOUNTS), color = "white", linewidth = 0.1) +
    scale_fill_viridis_c(
      option = "plasma",
      name = "Generators",
      limits = c(scale_min, scale_max)  # shared scale
    ) +
    labs(subtitle = year) +
    theme_void() +
    theme(
      plot.title = element_text(hjust = 0.5, face = "bold", size = 14),
      legend.position = "right"
    )
}

# Calling the map function:
map2019 <- map_year(gencounts2019, 2019)
map2022 <- map_year(gencounts2022, 2022)
map2025 <- map_year(gencounts2025, 2025)

#Side-by-side Display:
library(patchwork)
all_years <- map2019 + map2022 + map2025 + 
  plot_layout(guides = "collect") +  # merges the three legends into one
  plot_annotation(
    title = "Solar Generators per Census Tract by Year",
    caption = "Source: IPA Illinois Shines Block Grant & Solar For All Applications",
    
    theme = theme(plot.title = element_text(hjust = 0.5, face = "bold", size = 16))
  )

all_years


  #Number of generators
year2019 <- tractsandsolar %>% filter(YEAR == 2019)
year2019 %>% dim()
gencounts2019 <- year2019 %>% 
  group_by(GEOID,geometry) %>% 
  summarize('GENCOUNTS' = n(), .groups = 'drop') %>% 
  st_as_sf() 
gencounts2019 %>% summary()

#Data sources:
year2019 %>% colnames()
year2019 %>% group_by(source_file) %>% summarize(n = n())
year2019$source_file %>% unique()

# Mapping:
full_map_2019 <- ggplot(gencounts2019) +
  geom_sf(data=cook_county, color = 'black') +
  geom_sf(data=tractsclean, color='black')+
  geom_sf(aes(fill = GENCOUNTS), color = "skyblue", linewidth = 0.1) +
  scale_fill_viridis_c(
    option = "plasma",
    name = "Generators",
    limits = c(scale_min, scale_max),
    na.value = "grey80",
  ) +
  labs(
    title = paste("Solar Generators per Census Tract (2019)"),
    caption = "Source: IPA Illinois Shines Block Grant Applications"
  ) +
  theme_void() +
  theme(
    plot.title = element_text(hjust = 0.5, face = "bold", size = 14),
    legend.position = "right"
  )

full_map_2019

  #Capacity 
capcounts2019 <- year2019 %>% 
  group_by('GEOID') %>% 
  summarize('CAPACITY' = sum(kw))




# Mapping Plant IDs for Time Period 2: ------------------------------------

year2022 <- tractsandsolar %>% filter(YEAR == 2022)
year2022 %>% dim()
gencounts2022 <- year2022 %>% 
  group_by(GEOID,geometry) %>% 
  summarize('GENCOUNTS' = n(), .groups = 'drop') %>% 
  st_as_sf() 
gencounts2022 %>% summary()

#Data sources:
year2022 %>% group_by(source_file) %>% summarize(n = n())
year2022$source_file %>% unique()

# Mapping:
full_map_2022 <- ggplot(gencounts2022) +
  geom_sf(data=cook_county, color = 'black') +
  geom_sf(data=tractsclean, color='black')+
  geom_sf(aes(fill = GENCOUNTS), color = "skyblue", linewidth = 0.1) +
  scale_fill_viridis_c(
    option = "plasma",
    name = "Generators",
    limits = c(scale_min, scale_max),
    na.value = "grey80"
  ) +
  labs(
    title = paste("Solar Generators per Census Tract (2022)"),
    caption = "Source: IPA Illinois Shines Block Grant & Solar For All Applications"
  ) +
  theme_void() +
  theme(
    plot.title = element_text(hjust = 0.5, face = "bold", size = 14),
    legend.position = "right"
  )

full_map_2022



# Mapping Plant IDs for Time Period 3: ------------------------------------

year2025 <- tractsandsolar %>% filter(YEAR == 2025)
year2025 %>% dim()
gencounts2025 <- year2025 %>% 
  group_by(GEOID,geometry) %>% 
  summarize('GENCOUNTS' = n(), .groups = 'drop') %>% 
  st_as_sf() 
gencounts2025 %>% summary()

#Data sources:
year2025 %>% group_by(source_file) %>% summarize(n = n())
year2025$source_file %>% unique()

# Mapping:
full_map_2025 <- ggplot(gencounts2025) +
  geom_sf(data=cook_county, color = 'black') +
  geom_sf(data=tractsclean, color='black')+
  geom_sf(aes(fill = GENCOUNTS), color = "skyblue", linewidth = 0.1) +
  scale_fill_viridis_c(
    option = "plasma",
    name = "Generators",
    limits = c(scale_min, scale_max),
    na.value = "grey80"
  ) +
  labs(
    title = paste("Solar Generators per Census Tract (2025)"),
    caption = "Source: IPA Illinois Shines Block Grant & Solar For All Applications"
  ) +
  theme_void() +
  theme(
    plot.title = element_text(hjust = 0.5, face = "bold", size = 14),
    legend.position = "right"
  )

full_map_2025

# Cook County Basemap with Census Tracts:

ggplot() +
  geom_sf(data=cook_county, color = 'black') +
  geom_sf(data=tractsclean, color='black')+
  # scale_fill_gradient(low='lightblue', high='darkmagenta', na.value = 'grey90') +
  theme_void() +
  labs(title = "Cook County")



# Saving Maps to directory: ------------------------------------

directory <- '/Users/griffinberonio/Documents/AAE 724/genmaps'
full_map_2019
path <- paste(directory,'2019_full')








-- locations

create table public.locations (
  location_id bigint not null,
  latitude double precision null,
  longitude double precision null,
  elevation bigint null,
  utc_offset_seconds bigint null,
  timezone text null,
  timezone_abbreviation text null,
  city_name text null,
  constraint locations_pkey primary key (location_id)
) TABLESPACE pg_default;

-- weather_data

create table public.weather_data (
  location_id bigint null,
  timestamp timestamp with time zone null,
  temperature double precision null,
  humidity bigint null,
  wind_speed double precision null,
  precipitation text null,
  wind_direction bigint null,
  cloud_cover bigint null,
  dew_point double precision null,
  apparent_temperature double precision null,
  rain text null,
  snowfall text null,
  snow_depth text null,
  pressure_msl double precision null,
  weather_code bigint null,
  surface_pressure double precision null,
  cloud_cover_low bigint null,
  cloud_cover_mid bigint null,
  cloud_cover_high bigint null,
  evapotranspiration double precision null,
  vapour_pressure_deficit double precision null,
  wind_gusts double precision null,
  soil_temperature double precision null,
  soil_moisture double precision null
) TABLESPACE pg_default;




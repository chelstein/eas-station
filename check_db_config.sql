-- Check receiver configuration
SELECT 
    identifier,
    display_name,
    driver,
    frequency_hz / 1000000.0 as frequency_mhz,
    sample_rate / 1000000.0 as iq_sample_rate_mhz,
    audio_sample_rate,
    modulation_type,
    audio_output,
    enabled,
    auto_start
FROM radio_receivers
WHERE identifier = 'wxj93';

-- Check audio source configuration
SELECT 
    name,
    source_type,
    enabled,
    auto_start,
    priority,
    config_params
FROM audio_source_configs
WHERE name LIKE '%wxj93%' OR name LIKE '%WXJ93%';

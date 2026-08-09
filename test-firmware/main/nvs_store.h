#pragma once

#include "esp_err.h"
#include <stdbool.h>

esp_err_t nvs_store_init(void);
esp_err_t nvs_store_set_wifi(const char *ssid, const char *password);
bool      nvs_store_get_wifi(char *ssid, size_t ssid_len, char *password, size_t pass_len);
esp_err_t nvs_store_erase_wifi(void);

/* The MQTT broker the DUT was told to use, entered in the captive portal
 * alongside the credentials. Empty means "not configured": the DUT then
 * falls back to the gateway of its own DHCP lease, which on this bench is
 * the bench itself. */
esp_err_t nvs_store_set_broker(const char *uri);
bool      nvs_store_get_broker(char *uri, size_t uri_len);

#pragma once

#include "esp_err.h"
#include <stdbool.h>

esp_err_t nvs_store_init(void);
esp_err_t nvs_store_set_wifi(const char *ssid, const char *password);
bool      nvs_store_get_wifi(char *ssid, size_t ssid_len, char *password, size_t pass_len);
esp_err_t nvs_store_erase_wifi(void);

/* A named access point the DUT raises instead of joining anything, so the
 * bench can be tested as a *station* without an external network.
 *
 * The bench has one radio: it cannot be the AP the tests join. Its own
 * provisioning portal is open by design, which leaves the WPA2 paths — a
 * correct passphrase accepted, a wrong one refused — with nothing to aim
 * at. This entry gives the same board, the one already under test, a second
 * job. Empty password means an open AP.
 *
 * Set through the serial console, and cleared by `nvs_store_set_wifi`: a
 * DUT that has just been handed credentials is going back to being a
 * station, so provisioning always returns it to normal without a second
 * command anyone could forget. */
esp_err_t nvs_store_set_test_ap(const char *ssid, const char *password);
bool      nvs_store_get_test_ap(char *ssid, size_t ssid_len,
                                char *password, size_t pass_len);
esp_err_t nvs_store_clear_test_ap(void);

/* The MQTT broker the DUT was told to use, entered in the captive portal
 * alongside the credentials. Empty means "not configured": the DUT then
 * falls back to the gateway of its own DHCP lease, which on this bench is
 * the bench itself. */
esp_err_t nvs_store_set_broker(const char *uri);
bool      nvs_store_get_broker(char *uri, size_t uri_len);

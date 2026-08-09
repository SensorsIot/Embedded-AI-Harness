#pragma once

#include "esp_err.h"
#include <stdbool.h>

#include <stddef.h>

esp_err_t wifi_prov_init(void);
void      wifi_prov_reset(void);
bool      wifi_prov_is_connected(void);
bool      wifi_prov_is_ap_mode(void);

/* Fill `out` with "<rssi> <ch> <auth> <ssid>" lines for what the DUT can
 * hear, newline-separated. Returns the number of APs, or -1 on failure.
 *
 * The bench can scan, and the DUT could not — so when the two failed to
 * meet there was no way to tell "the AP is not beaconing" from "this
 * receiver is deaf". One radio reporting is an assertion; two radios
 * reporting is a measurement. */
int  wifi_prov_scan(char *out, size_t out_sz);

/* Dotted-quad of the STA interface, or "0.0.0.0" when not connected. */
void wifi_prov_get_ip(char *out, size_t out_sz);

/* Station MAC as "aa:bb:cc:dd:ee:ff". */
void wifi_prov_get_mac(char *out, size_t out_sz);

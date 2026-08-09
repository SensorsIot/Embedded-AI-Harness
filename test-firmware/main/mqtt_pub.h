#pragma once

#include "esp_err.h"
#include <stdbool.h>

/* Start the MQTT client and publish periodically.
 *
 * `fallback_host` is used when the captive portal was submitted without a
 * broker — normally the gateway of the DUT's own lease, which on this bench
 * is the bench itself. */
esp_err_t   mqtt_pub_start(const char *fallback_host);
bool        mqtt_pub_is_connected(void);
const char *mqtt_pub_topic(void);

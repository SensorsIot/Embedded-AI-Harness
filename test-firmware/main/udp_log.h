#pragma once

#include "esp_err.h"

esp_err_t udp_log_init(const char *host, uint16_t port);

/* Redirect the log stream to a new destination.
   Logging starts before WiFi does, so the first destination is a guess; this
   corrects it once the DHCP lease names the bench that handed it out. */
void      udp_log_set_host(const char *host);

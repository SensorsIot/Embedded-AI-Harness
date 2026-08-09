#pragma once

#include "esp_err.h"

/* Line-oriented command console on the DUT's USB serial port.
   Commands: ping | status | wifi <ssid> [pass] | forget | reboot
   Every command answers with one line beginning OK or ERR. */
esp_err_t serial_console_init(void);

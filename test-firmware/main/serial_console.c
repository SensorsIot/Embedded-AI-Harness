/* A line-oriented console on the DUT's USB serial port.
 *
 * Two things the bench could not do without it:
 *
 * 1. **Provision over serial.** Credentials used to arrive only through the
 *    captive portal, which needs the DUT's own AP to be on the air. When it
 *    is not — a radio that will not transmit, a board in a shielded corner,
 *    stale credentials for a network that no longer exists — there was no
 *    way in at all, and no way to tell "the AP is broken" from "the AP is
 *    fine and nobody can see it". Serial is a wire; it does not have that
 *    failure mode.
 *
 * 2. **Answer.** FR-030 says a byte written to a slot reaches the device,
 *    and the bench owned nothing that would say anything back — so the test
 *    borrowed a project's simulator and went red when that project shipped.
 *    `ping` answers `OK pong`.
 *
 * Deliberately not a shell: fixed verbs, one line in, one line out, no
 * echo, no editing, no prompt. Anything reading this port is a program.
 */

#include "serial_console.h"
#include "nvs_store.h"
#include "wifi_prov.h"

#include "driver/usb_serial_jtag.h"
#include "esp_log.h"
#include "esp_system.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include <stdarg.h>
#include <stdio.h>
#include <string.h>

static const char *TAG = "console";

#define LINE_MAX   192
#define RX_CHUNK   64

static void reply(const char *fmt, ...)
{
    /* Replies go through printf so they land in the same stream as the logs
       and the bench's recorder sees them without special handling. */
    va_list args;
    va_start(args, fmt);
    vprintf(fmt, args);
    va_end(args);
    fputc('\n', stdout);
    fflush(stdout);
}

/* "wifi <ssid> <password>" — password may be empty for an open network. */
static void cmd_wifi(char *rest)
{
    char *ssid = rest;
    while (*ssid == ' ') ssid++;
    if (*ssid == '\0') {
        reply("ERR wifi needs an ssid");
        return;
    }
    char *pass = strchr(ssid, ' ');
    if (pass) {
        *pass++ = '\0';
        while (*pass == ' ') pass++;
    } else {
        pass = "";
    }
    nvs_store_set_wifi(ssid, pass);
    reply("OK wifi stored ssid=%s pass_len=%d — rebooting", ssid, (int)strlen(pass));
    vTaskDelay(pdMS_TO_TICKS(300));
    esp_restart();
}

static void handle_line(char *line)
{
    while (*line == ' ') line++;
    if (*line == '\0') return;

    char *rest = strchr(line, ' ');
    if (rest) *rest++ = '\0'; else rest = "";

    if (!strcmp(line, "ping")) {
        /* The one command that exists purely to be answered. */
        reply("OK pong");
    } else if (!strcmp(line, "status")) {
        reply("OK status wifi=%d ap_mode=%d",
              wifi_prov_is_connected() ? 1 : 0,
              wifi_prov_is_ap_mode() ? 1 : 0);
    } else if (!strcmp(line, "wifi")) {
        cmd_wifi(rest);
    } else if (!strcmp(line, "forget")) {
        nvs_store_erase_wifi();
        reply("OK forget — rebooting into the provisioning portal");
        vTaskDelay(pdMS_TO_TICKS(300));
        esp_restart();
    } else if (!strcmp(line, "reboot")) {
        reply("OK reboot");
        vTaskDelay(pdMS_TO_TICKS(300));
        esp_restart();
    } else {
        /* Name what was not understood. A bare "ERR" tells a caller nothing
           about whether it mistyped or is talking to the wrong device. */
        reply("ERR unknown command '%s' — try ping|status|wifi|forget|reboot",
              line);
    }
}

static void console_task(void *arg)
{
    char line[LINE_MAX];
    size_t len = 0;
    uint8_t chunk[RX_CHUNK];

    while (1) {
        int n = usb_serial_jtag_read_bytes(chunk, sizeof(chunk),
                                           pdMS_TO_TICKS(200));
        for (int i = 0; i < n; i++) {
            char c = (char)chunk[i];
            if (c == '\r') continue;
            if (c == '\n') {
                line[len] = '\0';
                handle_line(line);
                len = 0;
            } else if (len < sizeof(line) - 1) {
                line[len++] = c;
            } else {
                /* Overlong input is discarded whole rather than silently
                   truncated into a different command. */
                len = 0;
                reply("ERR line too long");
            }
        }
    }
}

esp_err_t serial_console_init(void)
{
    usb_serial_jtag_driver_config_t cfg = USB_SERIAL_JTAG_DRIVER_CONFIG_DEFAULT();
    esp_err_t err = usb_serial_jtag_driver_install(&cfg);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "usb_serial_jtag driver install failed: %s",
                 esp_err_to_name(err));
        return err;
    }
    xTaskCreate(console_task, "console", 4096, NULL, 5, NULL);
    ESP_LOGI(TAG, "serial console ready — ping|status|wifi|forget|reboot");
    return ESP_OK;
}

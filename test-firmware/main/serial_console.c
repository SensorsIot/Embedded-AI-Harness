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
#include "mqtt_pub.h"

#include "driver/usb_serial_jtag.h"
#include "esp_app_desc.h"
#include "esp_wifi.h"
#include "esp_log.h"
#include "esp_system.h"
#include <stdlib.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include <stdarg.h>
#include <stdio.h>
#include <string.h>

static const char *TAG = "console";

#define CONSOLE_LINE_MAX   192   /* LINE_MAX belongs to limits.h */
#define RX_CHUNK   64
#define SCAN_BUF   2048          /* 20 APs × ~64 bytes, heap not stack */

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
        char ip[16], mac[18];
        wifi_prov_get_ip(ip, sizeof(ip));
        wifi_prov_get_mac(mac, sizeof(mac));
        reply("OK status wifi=%d ap_mode=%d ip=%s mac=%s mqtt=%d topic=%s",
              wifi_prov_is_connected() ? 1 : 0,
              wifi_prov_is_ap_mode() ? 1 : 0, ip, mac,
              mqtt_pub_is_connected() ? 1 : 0, mqtt_pub_topic());
    } else if (!strcmp(line, "scan")) {
        /* The DUT's own view of the air. Without it, a DUT that will not
         * join the bench AP is indistinguishable from a bench AP that is
         * not beaconing — both look like NO_AP_FOUND from one side only. */
        char *buf = malloc(SCAN_BUF);
        if (!buf) {
            reply("ERR scan out of memory");
        } else {
            int n = wifi_prov_scan(buf, SCAN_BUF);
            if (n < 0) {
                reply("ERR scan failed");
            } else {
                reply("OK scan %d", n);
                /* One AP per line, already newline-terminated, so a reader
                   can match on an SSID without parsing a list format. */
                fputs(buf, stdout);
                fflush(stdout);
                reply("OK scan end");
            }
            free(buf);
        }
    } else if (!strcmp(line, "info")) {
        const esp_app_desc_t *app = esp_app_get_description();
        int8_t txp = 0;
        esp_wifi_get_max_tx_power(&txp);
        reply("OK info project=%s version=%s idf=%s txpower=%d(%.2fdBm)",
              app->project_name, app->version, app->idf_ver,
              txp, txp / 4.0);
    } else if (!strcmp(line, "mark")) {
        /* An observable the bench can ask for at a moment of its choosing,
         * rather than waiting up to 10 s for the next heartbeat. */
        reply("OK mark %s", rest);
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
        reply("ERR unknown command '%s' — try "
              "ping|status|scan|info|mark|wifi|forget|reboot", line);
    }
}

static void console_task(void *arg)
{
    char line[CONSOLE_LINE_MAX];
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
    ESP_LOGI(TAG, "serial console ready — "
                  "ping|status|scan|info|mark|wifi|forget|reboot");
    return ESP_OK;
}

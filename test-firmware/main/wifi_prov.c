#include "wifi_prov.h"
#include "nvs_store.h"
#include "udp_log.h"
#include "esp_wifi.h"
#include "esp_log.h"
#include "esp_mac.h"
#include "esp_http_server.h"
#include "esp_netif.h"
#include "esp_event.h"
#include "lwip/inet.h"
#include "dns_server.h"
#include "cJSON.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include <string.h>
#include <stdlib.h>
#include <stdio.h>

static const char *TAG = "wifi_prov";

#define AP_SSID        "WB-Test-Setup"
#define STA_MAX_RETRY  20

extern const char portal_html_start[] asm("_binary_portal_html_start");
extern const char portal_html_end[]   asm("_binary_portal_html_end");

static int s_retry_count = 0;
static bool s_sta_connected = false;
static bool s_ap_mode = false;
static volatile bool s_scanning = false;
static httpd_handle_t s_server = NULL;

/* ── Event handlers ────────────────────────────────────────────── */

static void wifi_event_handler(void *arg, esp_event_base_t base,
                               int32_t id, void *data)
{
    if (base == WIFI_EVENT) {
        switch (id) {
        case WIFI_EVENT_STA_START:
            /* In portal mode the station exists only to carry a scan. */
            if (!s_scanning)
                esp_wifi_connect();
            break;
        case WIFI_EVENT_STA_DISCONNECTED: {
            wifi_event_sta_disconnected_t *dis = data;
            s_sta_connected = false;
            if (s_scanning) {
                /* A scan needs the station idle, and this handler is what
                   makes it never idle: every disconnect re-arms a connect,
                   so "STA is connecting, scan are not allowed" is the state
                   the retry loop guarantees. Stand down for the scan. */
                break;
            }
            if (s_retry_count < STA_MAX_RETRY) {
                s_retry_count++;
                ESP_LOGW(TAG, "STA disconnect (reason=%d), retry %d/%d",
                         dis->reason, s_retry_count, STA_MAX_RETRY);
                esp_wifi_connect();
            } else {
                /* The bench raises a fresh AP with a random SSID for each
                   run, so the credentials in NVS are stale by design the
                   moment a run ends. A DUT that sits retrying a network
                   that no longer exists cannot be re-provisioned — its
                   portal is the only way in, and it is not running. Forget
                   them and come back up as the portal. */
                ESP_LOGE(TAG, "STA failed after %d retries (last reason=%d)"
                         " — clearing credentials and rebooting into the"
                         " provisioning portal",
                         STA_MAX_RETRY, dis->reason);
                nvs_store_erase_wifi();
                esp_restart();
            }
            break;
        }
        case WIFI_EVENT_AP_STACONNECTED: {
            wifi_event_ap_staconnected_t *e = data;
            ESP_LOGI(TAG, "AP: station " MACSTR " joined", MAC2STR(e->mac));
            break;
        }
        default:
            break;
        }
    } else if (base == IP_EVENT && id == IP_EVENT_STA_GOT_IP) {
        ip_event_got_ip_t *e = data;
        ESP_LOGI(TAG, "STA got IP: " IPSTR, IP2STR(&e->ip_info.ip));
        s_sta_connected = true;
        s_retry_count = 0;
        /* The bench hands out this lease, so the gateway is the bench.
           Send it the logs. The address used to be compiled in, which meant
           the firmware only ever logged to whichever bench was on that IP
           when someone last edited app_main — by now, none of them. */
        char gw[16];
        snprintf(gw, sizeof(gw), IPSTR, IP2STR(&e->ip_info.gw));
        udp_log_set_host(gw);
    }
}

/* ── Captive portal HTTP handlers ──────────────────────────────── */

static esp_err_t portal_get_handler(httpd_req_t *req)
{
    httpd_resp_set_type(req, "text/html");
    httpd_resp_send(req, portal_html_start, portal_html_end - portal_html_start);
    return ESP_OK;
}

/* URL-decode a string in-place. Returns decoded length. */
static int url_decode(char *s)
{
    char *dst = s;
    for (const char *src = s; *src; src++) {
        if (*src == '+') { *dst++ = ' '; }
        else if (*src == '%' && src[1] && src[2]) {
            char hex[3] = {src[1], src[2], 0};
            *dst++ = (char)strtol(hex, NULL, 16);
            src += 2;
        } else { *dst++ = *src; }
    }
    *dst = '\0';
    return (int)(dst - s);
}

/* Extract a value from URL-encoded form data: "key1=val1&key2=val2" */
static bool form_get(const char *body, const char *key, char *out, size_t out_sz)
{
    size_t klen = strlen(key);
    const char *p = body;
    while ((p = strstr(p, key)) != NULL) {
        if (p != body && *(p - 1) != '&') { p += klen; continue; }
        if (p[klen] != '=') { p += klen; continue; }
        p += klen + 1;
        const char *end = strchr(p, '&');
        size_t vlen = end ? (size_t)(end - p) : strlen(p);
        if (vlen >= out_sz) vlen = out_sz - 1;
        memcpy(out, p, vlen);
        out[vlen] = '\0';
        url_decode(out);
        return true;
    }
    return false;
}

static esp_err_t connect_post_handler(httpd_req_t *req)
{
    char buf[256];
    int len = httpd_req_recv(req, buf, sizeof(buf) - 1);
    if (len <= 0) {
        httpd_resp_send_err(req, HTTPD_400_BAD_REQUEST, "No body");
        return ESP_FAIL;
    }
    buf[len] = '\0';

    char ssid_buf[33] = {0};
    char pass_buf[65] = {0};
    const char *ssid = NULL;
    const char *pass = NULL;

    /* Try JSON first, fall back to form-encoded */
    cJSON *json = cJSON_Parse(buf);
    if (json) {
        ssid = cJSON_GetStringValue(cJSON_GetObjectItem(json, "ssid"));
        pass = cJSON_GetStringValue(cJSON_GetObjectItem(json, "password"));
    } else {
        if (form_get(buf, "ssid", ssid_buf, sizeof(ssid_buf)))
            ssid = ssid_buf;
        form_get(buf, "password", pass_buf, sizeof(pass_buf));
        pass = pass_buf;
    }

    if (!ssid || strlen(ssid) == 0) {
        if (json) cJSON_Delete(json);
        httpd_resp_send_err(req, HTTPD_400_BAD_REQUEST, "Missing SSID");
        return ESP_FAIL;
    }

    nvs_store_set_wifi(ssid, pass ? pass : "");
    if (json) cJSON_Delete(json);

    httpd_resp_set_type(req, "application/json");
    httpd_resp_sendstr(req, "{\"status\":\"ok\",\"message\":\"Rebooting...\"}");

    ESP_LOGI(TAG, "Credentials saved, rebooting in 1s...");
    vTaskDelay(pdMS_TO_TICKS(1000));
    esp_restart();
    return ESP_OK;
}

static esp_err_t redirect_handler(httpd_req_t *req, httpd_err_code_t err)
{
    httpd_resp_set_status(req, "302 Temporary Redirect");
    httpd_resp_set_hdr(req, "Location", "/");
    httpd_resp_send(req, "Redirect to captive portal", HTTPD_RESP_USE_STRLEN);
    return ESP_OK;
}

static void start_portal_server(void)
{
    httpd_config_t config = HTTPD_DEFAULT_CONFIG();
    config.max_open_sockets = 7;
    config.lru_purge_enable = true;

    if (httpd_start(&s_server, &config) != ESP_OK) {
        ESP_LOGE(TAG, "Failed to start HTTP server");
        return;
    }

    static const httpd_uri_t portal_get = {
        .uri = "/", .method = HTTP_GET, .handler = portal_get_handler
    };
    static const httpd_uri_t connect_post = {
        .uri = "/connect", .method = HTTP_POST, .handler = connect_post_handler
    };

    httpd_register_uri_handler(s_server, &portal_get);
    httpd_register_uri_handler(s_server, &connect_post);
    httpd_register_err_handler(s_server, HTTPD_404_NOT_FOUND, redirect_handler);

    ESP_LOGI(TAG, "Portal HTTP server started");
}

/* ── STA mode ──────────────────────────────────────────────────── */

static esp_err_t start_sta(const char *ssid, const char *password)
{
    esp_netif_create_default_wifi_sta();

    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));

    ESP_ERROR_CHECK(esp_event_handler_register(WIFI_EVENT, ESP_EVENT_ANY_ID, wifi_event_handler, NULL));
    ESP_ERROR_CHECK(esp_event_handler_register(IP_EVENT, IP_EVENT_STA_GOT_IP, wifi_event_handler, NULL));

    wifi_config_t wifi_cfg = {};
    strncpy((char *)wifi_cfg.sta.ssid, ssid, sizeof(wifi_cfg.sta.ssid) - 1);
    strncpy((char *)wifi_cfg.sta.password, password, sizeof(wifi_cfg.sta.password) - 1);

    /* Scan every channel and pick the strongest match, rather than taking
     * the first answer on the first channel that replies. A bench AP moves
     * channel between runs and shares the band with everything else in the
     * room; fast scan gives up early and reports NO_AP_FOUND for an AP that
     * is plainly on the air two channels up. */
    wifi_cfg.sta.scan_method = WIFI_ALL_CHANNEL_SCAN;
    wifi_cfg.sta.sort_method = WIFI_CONNECT_AP_BY_SIGNAL;

    /* Accept whatever security the AP offers instead of demanding WPA2.
     *
     * Supplying a password makes the default threshold WPA2, and an open
     * bench AP with the right SSID is then refused with reason 210
     * (NO_AP_FOUND_W_COMPATIBLE_SECURITY) — which reads in the log like the
     * AP was never there. A test DUT must join the bench AP as configured,
     * not as it wishes it were; the bench decides the security, not us. */
    wifi_cfg.sta.threshold.authmode = WIFI_AUTH_OPEN;
    wifi_cfg.sta.pmf_cfg.capable = true;
    wifi_cfg.sta.pmf_cfg.required = false;

    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA, &wifi_cfg));
    ESP_ERROR_CHECK(esp_wifi_start());

    /* No modem sleep. The station defaults to WIFI_PS_MIN_MODEM, which parks
     * the radio between beacons — and the EAPOL exchange that follows
     * association is exactly what gets lost when it does. The symptom is
     * reason 15, 4WAY_HANDSHAKE_TIMEOUT: the DUT associates, reaches `run`,
     * sits there and is dropped, over and over, while the AP logs an
     * association and no handshake at all. A bench DUT on USB power has
     * nothing to save. */
    esp_wifi_set_ps(WIFI_PS_NONE);

    /* Ask for full transmit power explicitly, and say what we actually got.
     *
     * A DUT that hears every AP in the building at normal levels and cannot
     * complete an association with any of them is failing on the transmit
     * side, and the two candidates are the antenna path and a radio that has
     * quietly settled on a low power. Only one of those is fixable in
     * software, and neither was distinguishable while nothing reported the
     * figure. 80 = 20 dBm, in the quarter-dBm units this API uses. */
    esp_wifi_set_max_tx_power(80);
    int8_t tx_power = 0;
    esp_wifi_get_max_tx_power(&tx_power);
    ESP_LOGI(TAG, "max tx power: %d (%.2f dBm)", tx_power, tx_power / 4.0);

    wifi_mode_t mode;
    esp_wifi_get_mode(&mode);
    ESP_LOGI(TAG, "STA mode=%d, connecting to '%s' (pass len=%d)", mode, ssid, (int)strlen(password));
    return ESP_OK;
}

/* ── AP mode with captive portal ───────────────────────────────── */

static esp_err_t start_ap(void)
{
    esp_netif_create_default_wifi_ap();

    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));

    ESP_ERROR_CHECK(esp_event_handler_instance_register(WIFI_EVENT,
                                                        ESP_EVENT_ANY_ID,
                                                        &wifi_event_handler,
                                                        NULL, NULL));

    wifi_config_t wifi_cfg = {
        .ap = {
            .ssid = AP_SSID,
            .ssid_len = strlen(AP_SSID),
            .channel = 1,
            .max_connection = 4,
            .authmode = WIFI_AUTH_OPEN,
        },
    };

    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_AP));
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_AP, &wifi_cfg));
    ESP_ERROR_CHECK(esp_wifi_start());

    ESP_LOGI(TAG, "AP started: SSID='%s' channel=1 auth=OPEN", AP_SSID);

    /* Captive portal HTTP + DNS */
    esp_log_level_set("httpd_uri", ESP_LOG_ERROR);
    esp_log_level_set("httpd_txrx", ESP_LOG_ERROR);
    esp_log_level_set("httpd_parse", ESP_LOG_ERROR);

    start_portal_server();

    dns_server_config_t dns_cfg = DNS_SERVER_CONFIG_SINGLE("*", "WIFI_AP_DEF");
    start_dns_server(&dns_cfg);

    ESP_LOGI(TAG, "AP mode: SSID='%s', portal at 192.168.4.1", AP_SSID);
    return ESP_OK;
}

/* ── Public API ────────────────────────────────────────────────── */

esp_err_t wifi_prov_init(void)
{
    char ssid[33] = {0};
    char pass[65] = {0};

    if (nvs_store_get_wifi(ssid, sizeof(ssid), pass, sizeof(pass))) {
        ESP_LOGI(TAG, "Found stored WiFi credentials");
        return start_sta(ssid, pass);
    }

    ESP_LOGI(TAG, "No WiFi credentials, starting AP provisioning");
    s_ap_mode = true;
    return start_ap();
}

void wifi_prov_reset(void)
{
    ESP_LOGW(TAG, "WiFi reset requested, erasing credentials and rebooting...");
    nvs_store_erase_wifi();
    vTaskDelay(pdMS_TO_TICKS(500));
    esp_restart();
}

bool wifi_prov_is_connected(void)
{
    return s_sta_connected;
}

bool wifi_prov_is_ap_mode(void)
{
    return s_ap_mode;
}

/* ── Reporting: what this radio can actually see and where it is ── */

#define SCAN_MAX_AP 20

static const char *auth_name(wifi_auth_mode_t m)
{
    switch (m) {
    case WIFI_AUTH_OPEN:            return "open";
    case WIFI_AUTH_WEP:             return "wep";
    case WIFI_AUTH_WPA_PSK:         return "wpa";
    case WIFI_AUTH_WPA2_PSK:        return "wpa2";
    case WIFI_AUTH_WPA_WPA2_PSK:    return "wpa/wpa2";
    case WIFI_AUTH_WPA3_PSK:        return "wpa3";
    case WIFI_AUTH_WPA2_WPA3_PSK:   return "wpa2/wpa3";
    default:                        return "other";
    }
}

int wifi_prov_scan(char *out, size_t out_sz)
{
    if (out_sz) out[0] = '\0';

    wifi_mode_t mode;
    if (esp_wifi_get_mode(&mode) != ESP_OK)
        return -1;

    /* A scan needs a station interface. In portal mode there is only an AP,
     * so borrow APSTA for the duration — the beacons keep going out, so a
     * bench that is mid-provisioning does not lose the portal it is talking
     * to just because it asked what else is on the air. */
    s_scanning = true;
    bool borrowed = false;
    if (mode == WIFI_MODE_AP) {
        if (esp_wifi_set_mode(WIFI_MODE_APSTA) != ESP_OK) {
            s_scanning = false;
            return -1;
        }
        borrowed = true;
    }

    /* Stop any connect attempt in flight. Scanning is refused outright while
     * the station is mid-connect, and a DUT holding stale credentials is
     * mid-connect essentially all the time — which is exactly when someone
     * wants to ask what it can see. A live association is left alone: the
     * radio can scan from connected, and dropping the link to answer a
     * question would break the test that asked. */
    if (!s_sta_connected) {
        esp_wifi_disconnect();
        vTaskDelay(pdMS_TO_TICKS(200));
    }

    wifi_scan_config_t cfg = { .show_hidden = true };
    esp_err_t err = esp_wifi_scan_start(&cfg, true);   /* blocking */
    if (err != ESP_OK) {
        ESP_LOGW(TAG, "scan failed: %s", esp_err_to_name(err));
        if (borrowed) esp_wifi_set_mode(WIFI_MODE_AP);
        s_scanning = false;
        return -1;
    }

    uint16_t found = 0;
    esp_wifi_scan_get_ap_num(&found);
    uint16_t want = found > SCAN_MAX_AP ? SCAN_MAX_AP : found;

    int written = 0;
    if (want) {
        wifi_ap_record_t *recs = calloc(want, sizeof(*recs));
        if (recs) {
            if (esp_wifi_scan_get_ap_records(&want, recs) == ESP_OK) {
                size_t used = 0;
                for (uint16_t i = 0; i < want; i++) {
                    int n = snprintf(out + used, out_sz - used,
                                     "%d %d %s %s\n",
                                     recs[i].rssi, recs[i].primary,
                                     auth_name(recs[i].authmode),
                                     (const char *)recs[i].ssid);
                    if (n < 0 || (size_t)n >= out_sz - used)
                        break;          /* truncate rather than overrun */
                    used += (size_t)n;
                    written++;
                }
            }
            free(recs);
        }
    }
    esp_wifi_scan_stop();

    if (borrowed) esp_wifi_set_mode(WIFI_MODE_AP);
    s_scanning = false;

    /* Put the station back to work. Answering a question must not leave the
     * DUT permanently not-trying-to-join. */
    if (!borrowed && !s_sta_connected)
        esp_wifi_connect();

    return written;
}

void wifi_prov_get_ip(char *out, size_t out_sz)
{
    esp_netif_ip_info_t ip = {0};
    esp_netif_t *netif = esp_netif_get_handle_from_ifkey("WIFI_STA_DEF");
    if (!netif || esp_netif_get_ip_info(netif, &ip) != ESP_OK) {
        snprintf(out, out_sz, "0.0.0.0");
        return;
    }
    snprintf(out, out_sz, IPSTR, IP2STR(&ip.ip));
}

void wifi_prov_get_mac(char *out, size_t out_sz)
{
    uint8_t mac[6] = {0};
    esp_wifi_get_mac(WIFI_IF_STA, mac);
    snprintf(out, out_sz, "%02x:%02x:%02x:%02x:%02x:%02x",
             mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
}


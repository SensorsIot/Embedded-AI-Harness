#include "nvs_store.h"
#include "nvs_flash.h"
#include "nvs.h"
#include "esp_log.h"
#include <string.h>

static const char *TAG = "nvs_store";
static const char *NVS_NAMESPACE = "wb_test";

esp_err_t nvs_store_init(void)
{
    esp_err_t err = nvs_flash_init();
    if (err == ESP_ERR_NVS_NO_FREE_PAGES || err == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_LOGW(TAG, "NVS corrupt, erasing...");
        ESP_ERROR_CHECK(nvs_flash_erase());
        err = nvs_flash_init();
    }
    ESP_ERROR_CHECK(err);
    ESP_LOGI(TAG, "NVS initialized");
    return ESP_OK;
}

esp_err_t nvs_store_set_broker(const char *uri)
{
    nvs_handle_t h;
    esp_err_t err = nvs_open(NVS_NAMESPACE, NVS_READWRITE, &h);
    if (err != ESP_OK) return err;
    err = nvs_set_str(h, "mqtt_broker", uri ? uri : "");
    if (err == ESP_OK) err = nvs_commit(h);
    nvs_close(h);
    ESP_LOGI(TAG, "MQTT broker saved: '%s'", uri ? uri : "");
    return err;
}

bool nvs_store_get_broker(char *uri, size_t uri_len)
{
    nvs_handle_t h;
    if (nvs_open(NVS_NAMESPACE, NVS_READONLY, &h) != ESP_OK) return false;
    size_t len = uri_len;
    esp_err_t err = nvs_get_str(h, "mqtt_broker", uri, &len);
    nvs_close(h);
    return err == ESP_OK && uri[0] != '\0';
}

esp_err_t nvs_store_set_test_ap(const char *ssid, const char *password)
{
    nvs_handle_t h;
    esp_err_t err = nvs_open(NVS_NAMESPACE, NVS_READWRITE, &h);
    if (err != ESP_OK) return err;
    err = nvs_set_str(h, "tap_ssid", ssid);
    if (err == ESP_OK) err = nvs_set_str(h, "tap_pass", password ? password : "");
    if (err == ESP_OK) err = nvs_commit(h);
    nvs_close(h);
    ESP_LOGI(TAG, "test AP saved (SSID: %s, pass_len: %d)",
             ssid, (int)(password ? strlen(password) : 0));
    return err;
}

bool nvs_store_get_test_ap(char *ssid, size_t ssid_len,
                           char *password, size_t pass_len)
{
    nvs_handle_t h;
    if (nvs_open(NVS_NAMESPACE, NVS_READONLY, &h) != ESP_OK) return false;
    esp_err_t err = nvs_get_str(h, "tap_ssid", ssid, &ssid_len);
    if (err == ESP_OK) {
        size_t pl = pass_len;
        /* An open test AP stores an empty string, and nvs_get_str is happy
           to return one — but a missing key must not leave the caller with
           an uninitialised buffer it then hands to esp_wifi. */
        if (nvs_get_str(h, "tap_pass", password, &pl) != ESP_OK)
            password[0] = '\0';
    }
    nvs_close(h);
    return err == ESP_OK && ssid[0] != '\0';
}

esp_err_t nvs_store_clear_test_ap(void)
{
    nvs_handle_t h;
    esp_err_t err = nvs_open(NVS_NAMESPACE, NVS_READWRITE, &h);
    if (err != ESP_OK) return err;
    nvs_erase_key(h, "tap_ssid");
    nvs_erase_key(h, "tap_pass");
    err = nvs_commit(h);
    nvs_close(h);
    return err;
}

esp_err_t nvs_store_set_wifi(const char *ssid, const char *password)
{
    nvs_handle_t h;
    esp_err_t err = nvs_open(NVS_NAMESPACE, NVS_READWRITE, &h);
    if (err != ESP_OK) return err;

    /* Being given credentials means going back to being a station. Clearing
       the test AP here rather than in a second command is what makes the
       recovery path the one the fixtures already take. */
    nvs_erase_key(h, "tap_ssid");
    nvs_erase_key(h, "tap_pass");

    err = nvs_set_str(h, "wifi_ssid", ssid);
    if (err == ESP_OK) {
        err = nvs_set_str(h, "wifi_pass", password);
    }
    if (err == ESP_OK) {
        err = nvs_commit(h);
    }
    nvs_close(h);
    ESP_LOGI(TAG, "WiFi credentials saved (SSID: %s)", ssid);
    return err;
}

bool nvs_store_get_wifi(char *ssid, size_t ssid_len, char *password, size_t pass_len)
{
    nvs_handle_t h;
    if (nvs_open(NVS_NAMESPACE, NVS_READONLY, &h) != ESP_OK) return false;

    esp_err_t err = nvs_get_str(h, "wifi_ssid", ssid, &ssid_len);
    if (err == ESP_OK) {
        err = nvs_get_str(h, "wifi_pass", password, &pass_len);
    }
    nvs_close(h);
    return (err == ESP_OK);
}

esp_err_t nvs_store_erase_wifi(void)
{
    nvs_handle_t h;
    esp_err_t err = nvs_open(NVS_NAMESPACE, NVS_READWRITE, &h);
    if (err != ESP_OK) return err;

    nvs_erase_key(h, "wifi_ssid");
    nvs_erase_key(h, "wifi_pass");
    err = nvs_commit(h);
    nvs_close(h);
    ESP_LOGI(TAG, "WiFi credentials erased");
    return err;
}

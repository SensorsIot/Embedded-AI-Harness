/* The DUT's MQTT client — the last step of the provisioning journey.
 *
 * WT-2104 asks whether a device that was handed credentials through a
 * captive portal ends up doing the thing it was provisioned *for*. Joining
 * an access point proves the radio; publishing to a broker proves the
 * whole chain — portal, credentials, DHCP, routing, and the broker the
 * operator typed into the form.
 *
 * It publishes on a timer rather than once at connect. A test that has to
 * be listening at the exact moment of a single publish is a race, and the
 * one it loses looks like a device that never published.
 */

#include "mqtt_pub.h"
#include "nvs_store.h"

#include "esp_log.h"
#include "esp_mac.h"
#include "esp_wifi.h"
#include "mqtt_client.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include <inttypes.h>
#include <stdio.h>
#include <string.h>

static const char *TAG = "mqtt_pub";

#define PUBLISH_PERIOD_MS  5000

static esp_mqtt_client_handle_t s_client;
static volatile bool s_connected;
static char s_topic[64];

bool mqtt_pub_is_connected(void)
{
    return s_connected;
}

const char *mqtt_pub_topic(void)
{
    return s_topic;
}

static void mqtt_event_handler(void *args, esp_event_base_t base,
                               int32_t event_id, void *event_data)
{
    switch ((esp_mqtt_event_id_t)event_id) {
    case MQTT_EVENT_CONNECTED:
        s_connected = true;
        ESP_LOGI(TAG, "connected to broker, publishing on %s", s_topic);
        break;
    case MQTT_EVENT_DISCONNECTED:
        s_connected = false;
        ESP_LOGW(TAG, "disconnected from broker");
        break;
    case MQTT_EVENT_ERROR:
        ESP_LOGW(TAG, "mqtt error");
        break;
    default:
        break;
    }
}

static void publish_task(void *arg)
{
    uint32_t seq = 0;
    char payload[128];
    while (1) {
        if (s_connected) {
            snprintf(payload, sizeof(payload),
                     "{\"seq\":%" PRIu32 ",\"src\":\"bench-dut\"}", seq++);
            esp_mqtt_client_publish(s_client, s_topic, payload, 0, 1, 0);
        }
        vTaskDelay(pdMS_TO_TICKS(PUBLISH_PERIOD_MS));
    }
}

esp_err_t mqtt_pub_start(const char *fallback_host)
{
    char broker[128] = {0};
    if (!nvs_store_get_broker(broker, sizeof(broker))) {
        /* Nothing was entered in the portal. The bench hands out this
         * device's lease, so its gateway is the bench, and the bench runs
         * the broker — a sensible default that still lets the portal
         * override it. */
        snprintf(broker, sizeof(broker), "mqtt://%s",
                 fallback_host ? fallback_host : "192.168.4.1");
        ESP_LOGI(TAG, "no broker configured, using %s", broker);
    } else if (!strstr(broker, "://")) {
        /* An operator types an address, not a URI. Accept both. */
        char host[128];
        snprintf(host, sizeof(host), "mqtt://%s", broker);
        strncpy(broker, host, sizeof(broker) - 1);
    }

    uint8_t mac[6] = {0};
    esp_wifi_get_mac(WIFI_IF_STA, mac);
    snprintf(s_topic, sizeof(s_topic),
             "workbench/dut/%02x%02x%02x%02x%02x%02x/hello",
             mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);

    esp_mqtt_client_config_t cfg = {
        .broker.address.uri = broker,
    };
    s_client = esp_mqtt_client_init(&cfg);
    if (!s_client) {
        ESP_LOGE(TAG, "client init failed for '%s'", broker);
        return ESP_FAIL;
    }
    esp_mqtt_client_register_event(s_client, ESP_EVENT_ANY_ID,
                                   mqtt_event_handler, NULL);
    esp_err_t err = esp_mqtt_client_start(s_client);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "client start failed: %s", esp_err_to_name(err));
        return err;
    }
    xTaskCreate(publish_task, "mqtt_pub", 4096, NULL, 4, NULL);
    ESP_LOGI(TAG, "broker=%s topic=%s", broker, s_topic);
    return ESP_OK;
}

idf_component_register(SRCS "app_main.c"
                            "nvs_store.c"
                            "udp_log.c"
                            "wifi_prov.c"
                            "ble_nus.c"
                            "ota_update.c"
                            "http_server.c"
                            "serial_console.c"
                            "mqtt_pub.c"
                       INCLUDE_DIRS "."
                       # esp-mqtt is not one of main's implicit requirements,
                       # so mqtt_client.h is not on the include path without
                       # asking for it by name.
                       REQUIRES mqtt
                       EMBED_FILES "portal.html")

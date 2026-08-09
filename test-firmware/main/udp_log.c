#include "udp_log.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/message_buffer.h"
#include "lwip/sockets.h"
#include <string.h>
#include <stdarg.h>
#include <stdbool.h>
#include <stdio.h>

static const char *TAG = "udp_log";

#define MSG_BUF_SIZE  4096
#define MAX_LOG_LINE  256

static MessageBufferHandle_t s_msg_buf;
static struct sockaddr_in s_dest_addr;
static vprintf_like_t s_orig_vprintf;

/* Re-entrancy guard. Anything logged from below this point — a failing
 * sendto, lwIP complaining that the network is down — comes straight back
 * through this hook, queues another line, and wakes the sender that logged
 * it. The task then never blocks, IDLE on its core never runs, and the task
 * watchdog fires: "CPU 1: udp_log". Observed on the bench DUT every time the
 * AP went away underneath it. */
static volatile bool s_in_hook;

static int udp_log_vprintf(const char *fmt, va_list args)
{
    /* A va_list is consumed by the call that reads it. Passing the same one
     * to vsnprintf afterwards is undefined behaviour, not a style problem:
     * it reads whatever the first traversal left behind. Copy it. */
    va_list copy;
    va_copy(copy, args);

    int ret = s_orig_vprintf(fmt, args);

    if (s_msg_buf && !s_in_hook) {
        s_in_hook = true;
        char buf[MAX_LOG_LINE];
        int len = vsnprintf(buf, sizeof(buf), fmt, copy);
        if (len > 0) {
            if (len >= (int)sizeof(buf)) len = sizeof(buf) - 1;
            /* Non-blocking: drop the line rather than stall the task that
             * is merely trying to log. This is a task context, so it is
             * xMessageBufferSend with a zero timeout — the FromISR variant
             * that used to be here is for interrupt context and its
             * behaviour outside one is not defined. */
            xMessageBufferSend(s_msg_buf, buf, len, 0);
        }
        s_in_hook = false;
    }
    va_end(copy);
    return ret;
}

static void udp_sender_task(void *arg)
{
    int sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_IP);
    if (sock < 0) {
        /* Not ESP_LOGE: that recurses through our own hook. Not
         * s_orig_vprintf with a fabricated va_list either — `(va_list){0}`
         * is not a valid va_list on any ABI, and constructing one to satisfy
         * a signature is undefined behaviour in the error path of a logger,
         * which is the worst possible place for it. fputs takes no varargs. */
        fputs("udp_log: failed to create socket\n", stdout);
        vTaskDelete(NULL);
        return;
    }

    char buf[MAX_LOG_LINE];
    while (1) {
        size_t len = xMessageBufferReceive(s_msg_buf, buf, sizeof(buf),
                                           portMAX_DELAY);
        if (len > 0) {
            sendto(sock, buf, len, 0,
                   (struct sockaddr *)&s_dest_addr, sizeof(s_dest_addr));
        } else {
            /* A receive that returns nothing must not become a busy loop on
             * a core whose IDLE task still has to run. */
            vTaskDelay(1);
        }
    }
}

esp_err_t udp_log_init(const char *host, uint16_t port)
{
    s_msg_buf = xMessageBufferCreate(MSG_BUF_SIZE);
    if (!s_msg_buf) return ESP_ERR_NO_MEM;

    memset(&s_dest_addr, 0, sizeof(s_dest_addr));
    s_dest_addr.sin_family = AF_INET;
    s_dest_addr.sin_port = htons(port);
    /* inet_aton() takes a dotted quad only — it does not resolve names. On
       failure it leaves the address at 0.0.0.0 and every log line goes nowhere,
       so fail loudly here rather than debugging silence later. */
    if (inet_aton(host, &s_dest_addr.sin_addr) == 0) {
        ESP_LOGE(TAG, "udp_log_init: '%s' is not an IPv4 address", host);
        vMessageBufferDelete(s_msg_buf);
        s_msg_buf = NULL;
        return ESP_ERR_INVALID_ARG;
    }

    xTaskCreate(udp_sender_task, "udp_log", 3072, NULL, 1, NULL);

    s_orig_vprintf = esp_log_set_vprintf(udp_log_vprintf);
    ESP_LOGI(TAG, "UDP logging -> %s:%d", host, port);
    return ESP_OK;
}

void udp_log_set_host(const char *host)
{
    struct in_addr addr;
    if (!host || inet_aton(host, &addr) == 0) {
        ESP_LOGE(TAG, "udp_log_set_host: '%s' is not an IPv4 address",
                 host ? host : "(null)");
        return;
    }
    /* One word, written atomically on every part this runs on — the sender
       task may be mid-loop, and the worst it can do is send one line to the
       previous destination. */
    s_dest_addr.sin_addr = addr;
    ESP_LOGI(TAG, "UDP logging redirected -> %s", host);
}

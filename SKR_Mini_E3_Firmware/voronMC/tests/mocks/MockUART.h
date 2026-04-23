/*
 * MockUART.h
 *
 *  Created on: 3 Apr 2026
 *      Author: f402n
 */

#ifndef MOCKS_MOCKUART_H_
#define MOCKS_MOCKUART_H_

#include <IHAL/IUART.h>
#include <vector>

class MockUART : public IUART {
public:
    IUART_StatusTypeDef UART_Transmit(const uint8_t* data, uint16_t len) override {
        tx_call_count++;
        last_tx_message.assign(data, data + len);
        tx_history.push_back(std::vector<uint8_t>(data, data + len));
        return IUART_OK;
    }

    IUART_StatusTypeDef UART_Receive(uint8_t* data, uint16_t len) override {
        rx_call_count++;
        if (rx_buffer.size() < len) return IUART_TIMEOUT;
        std::copy(rx_buffer.begin(), rx_buffer.begin() + len, data);
        rx_buffer.erase(rx_buffer.begin(), rx_buffer.begin() + len);
        return IUART_OK;
    }

    void flushRx(void) override {}

    // pre-load receive buffer with response bytes
    void loadRxBuffer(const uint8_t* data, uint16_t len) {
        rx_buffer.insert(rx_buffer.end(), data, data + len);
    }

    // find a write datagram for a specific register in tx_history
    std::vector<uint8_t> findWriteForReg(uint8_t reg) {
        for (auto& msg : tx_history) {
            if (msg.size() == 8 &&
                msg[0] == 0x05 &&
                (msg[2] & 0x80) &&
                (msg[2] & ~0x80) == reg) {
                return msg;
            }
        }
        return {};  // not found
    }

    void clearHistory(void) {
        tx_history.clear();
        last_tx_message.clear();
        rx_buffer.clear();
        tx_call_count = 0;
        rx_call_count = 0;
    }

    std::vector<uint8_t> last_tx_message;
    std::vector<uint8_t> rx_buffer;
    std::vector<std::vector<uint8_t>> tx_history;
    int tx_call_count = 0;
    int rx_call_count = 0;
};

#endif /* MOCKS_MOCKUART_H_ */

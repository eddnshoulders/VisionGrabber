#ifndef MOCKS_MOCKTMC2209_H_
#define MOCKS_MOCKTMC2209_H_

#include <IHAL/IUART.h>
#include "MockUART.h"
#include "TMC2209.h"
#include <map>
#include <cstdint>

static constexpr uint8_t TMC_SYNC_BYTE   = 0x05;
static constexpr uint8_t TMC_WRITE_BIT   = 0x80;
static constexpr uint8_t TMC_WRITE_LEN   = 8;
static constexpr uint8_t TMC_READ_REQ_LEN = 4;
static constexpr uint8_t TMC_READ_RSP_LEN = 8;

class MockTMC2209 {
public:
    MockTMC2209(MockUART& mockuart, uint8_t slave_addr)
        : mockuart_(mockuart), slave_addr_(slave_addr)
    {}

    // call after each UART_Transmit to process the datagram
    void process() {
        std::vector<uint8_t>& pkt = mockuart_.last_tx_message;

        if (pkt.empty()) return;
        if (pkt[0] != TMC_SYNC_BYTE) return;
        if (pkt[1] != slave_addr_) return;

        if (pkt.size() == TMC_WRITE_LEN) {
            // write datagram
            uint8_t reg = pkt[2] & ~TMC_WRITE_BIT;
            uint32_t value = ((uint32_t)pkt[3] << 24) |
                             ((uint32_t)pkt[4] << 16) |
                             ((uint32_t)pkt[5] << 8)  |
                             ((uint32_t)pkt[6]);
            registers[reg] = value;
            ifcnt_ = (ifcnt_ + 1) & 0xFF;  // increment IFCNT on each write
            decodeRegister(reg, value);

        } else if (pkt.size() == TMC_READ_REQ_LEN) {
            // read request -- prepare response in rx_buffer
            uint8_t reg = pkt[2];
            uint32_t value = registers[reg];

            uint8_t response[TMC_READ_RSP_LEN];
            response[0] = TMC_SYNC_BYTE;
            response[1] = 0xFF;  // master address
            response[2] = reg;
            response[3] = (value >> 24) & 0xFF;
            response[4] = (value >> 16) & 0xFF;
            response[5] = (value >> 8)  & 0xFF;
            response[6] = (value >> 0)  & 0xFF;
            response[7] = calcCRC(response, 7);

            mockuart_.loadRxBuffer(response, TMC_READ_RSP_LEN);
        }
    }

    // register map
    std::map<uint8_t, uint32_t> registers;

    // decoded register fields -- readable by tests
    uint8_t  irun           = 0;
    uint8_t  ihold          = 0;
    uint8_t  ihold_delay    = 0;
    uint8_t  microsteps     = 0;
    uint8_t  sg_threshold   = 0;
    uint32_t tcool_threshold = 0;
    uint32_t tpowerdown     = 0;
    bool     en_spreadcycle  = false;
    bool     pdn_disable     = false;
    bool     mstep_reg_select = false;

private:
    MockUART& mockuart_;
    uint8_t slave_addr_;
    uint8_t ifcnt_ = 0;

    uint8_t calcCRC(uint8_t* data, uint8_t len) {
        uint8_t crc = 0;
        for (uint8_t i = 0; i < len; i++) {
            uint8_t byte = data[i];
            for (uint8_t j = 0; j < 8; j++) {
                if ((crc >> 7) ^ (byte & 0x01)) {
                    crc = (crc << 1) ^ 0x07;
                } else {
                    crc = crc << 1;
                }
                byte >>= 1;
            }
        }
        return crc;
    }

    void decodeRegister(uint8_t reg, uint32_t value) {
        switch (reg) {
            case 0x00:  // GCONF
                en_spreadcycle   = (value >> 2) & 0x01;
                pdn_disable      = (value >> 6) & 0x01;
                mstep_reg_select = (value >> 7) & 0x01;
                break;
            case 0x10:  // IHOLD_IRUN
                ihold      = (value >> 0)  & 0x1F;
                irun       = (value >> 8)  & 0x1F;
                ihold_delay = (value >> 16) & 0x0F;
                break;
            case 0x6C:  // CHOPCONF
                microsteps = (value >> 24) & 0x0F;  // MRES bits
                break;
            case 0x11:  // TPOWERDOWN
                tpowerdown = value & 0xFF;
                break;
            case 0x14:  // TCOOLTHRS
                tcool_threshold = value & 0xFFFFF;
                break;
            case 0x40:  // SGTHRS
                sg_threshold = value & 0xFF;
                break;
            default:
                break;
        }
    }
};

#endif /* MOCKS_MOCKTMC2209_H_ */

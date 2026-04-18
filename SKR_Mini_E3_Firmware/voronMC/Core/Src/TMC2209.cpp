/*
 * TMS2209.cpp
 *
 *  Created on: 30 Mar 2026
 *      Author: f402n
 */

// TMC2209.cpp
#include "TMC2209.h"
#include <cstring>

static constexpr uint8_t SYNC_BYTE    = 0x05;
static constexpr uint8_t WRITE_BIT    = 0x80;
static constexpr uint16_t WRITE_LEN    = 8;
static constexpr uint16_t READ_REQ_LEN = 4;
static constexpr uint16_t READ_RSP_LEN = 8;

// Register addresses
static constexpr uint8_t REG_GCONF      = 0x00;
static constexpr uint8_t REG_IFCNT      = 0x02;
static constexpr uint8_t REG_IHOLD_IRUN = 0x10;
static constexpr uint8_t REG_CHOPCONF   = 0x6C;
static constexpr uint8_t REG_SGTHRS     = 0x40;
static constexpr uint8_t REG_SG_RESULT  = 0x41;
static constexpr uint8_t REG_TCOOLTHRS  = 0x14;
static constexpr uint8_t REG_TPOWERDOWN	= 0x11;


TMC2209::TMC2209(IUART& iuart, uint8_t slave_addr)
    : iuart_(iuart), slave_addr_(slave_addr) {}

void TMC2209::flushRx() { iuart_.flushRx(); }

uint8_t TMC2209::calcCRC(uint8_t* data, uint8_t len) {
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

void TMC2209::writeRegister(uint8_t reg, uint32_t data) {
    uint8_t packet[WRITE_LEN];
    packet[0] = SYNC_BYTE;
    packet[1] = slave_addr_;
    packet[2] = reg | WRITE_BIT;
    packet[3] = (data >> 24) & 0xFF;
    packet[4] = (data >> 16) & 0xFF;
    packet[5] = (data >> 8)  & 0xFF;
    packet[6] = (data >> 0)  & 0xFF;
    packet[7] = calcCRC(packet, 7);

    IUART_StatusTypeDef status = iuart_.UART_Transmit(packet, WRITE_LEN);
}

bool TMC2209::verifyWrite(uint8_t reg, uint32_t data) {
    uint32_t ifcnt_before = 0;
    uint32_t ifcnt_after  = 0;

    readRegister(REG_IFCNT, ifcnt_before);
    writeRegister(reg, data);
    readRegister(REG_IFCNT, ifcnt_after);

    // Handle wrap at 255
    uint8_t expected = (static_cast<uint8_t>(ifcnt_before) + 1) & 0xFF;
    return static_cast<uint8_t>(ifcnt_after) == expected;
}

bool TMC2209::readRegister(uint8_t reg, uint32_t& data) {
	IUART_StatusTypeDef status;

	// Send read request
    uint8_t request[READ_REQ_LEN];
    request[0] = SYNC_BYTE;
    request[1] = slave_addr_;
    request[2] = reg;
    request[3] = calcCRC(request, 3);

    status = iuart_.UART_Transmit(request, READ_REQ_LEN);
    //status = HAL_UART_Transmit(huart_, request, READ_REQ_LEN, 100);

    flushRx();  // clear echo overrun

    // Read response -- first 4 bytes are echo of request, next 8 are response
    uint8_t response[READ_RSP_LEN];
    status = iuart_.UART_Receive(response, READ_RSP_LEN);

    if (status != IUART_OK) return false;

    // Verify CRC
    uint8_t crc = calcCRC(response, 7);
    if (crc != response[7]) return false;

    // Extract data
    data = ((uint32_t)response[3] << 24) |
           ((uint32_t)response[4] << 16) |
           ((uint32_t)response[5] << 8)  |
           ((uint32_t)response[6]);

    return true;
}

bool TMC2209::isConnected() {
    uint32_t ifcnt = 0;
    return readRegister(REG_IFCNT, ifcnt);
}

uint8_t TMC2209::microstepsToBits(uint8_t microsteps) {
    switch (microsteps) {
        case 256: return 0;
        case 128: return 1;
        case 64:  return 2;
        case 32:  return 3;
        case 16:  return 4;
        case 8:   return 5;
        case 4:   return 6;
        case 2:   return 7;
        case 1:   return 8;
        default:  return 4;  // default 16 microsteps
    }
}

uint8_t TMC2209::bitsToMicrosteps(uint8_t bits) {
    switch (bits) {
        case 0: return 256;
        case 1: return 128;
        case 2: return 64;
        case 3: return 32;
        case 4: return 16;
        case 5: return 8;
        case 6: return 4;
        case 7: return 2;
        case 8: return 1;
        default: return 16;
    }
}

bool TMC2209::init(const TMC2209Config& config) {
    // Verify comms first
    if (!isConnected()) return false;

    // GCONF -- en_spreadCycle=1, PDN_UART=1, MSTEP_REG_SELECT=1
    uint32_t gconf = 0;
    gconf |= config.en_spreadcycle   ? (1UL << 2) : 0;
    gconf |= config.pdn_disable      ? (1UL << 6) : 0;
    gconf |= config.mstep_reg_select ? (1UL << 7) : 0;
    if (!verifyWrite(REG_GCONF, gconf)) return false;

    // IHOLD_IRUN -- set hold and run current
    uint32_t ihold_irun = ((uint32_t)config.hold_current & 0x1F) |
                          (((uint32_t)config.run_current & 0x1F) << 8) |
                          ((unsigned long)config.ihold_delay << 16);
    if (!verifyWrite(REG_IHOLD_IRUN, ihold_irun)) return false;

    // CHOPCONF -- set microstepping
    // TBL=1, TOFF=3 are safe defaults for most motors
    uint32_t chopconf = 0x10000053;  // defaults
    chopconf &= ~(0xFUL << 24);     // clear MRES bits
    chopconf |= ((uint32_t)microstepsToBits(config.microsteps) << 24);
    if (!verifyWrite(REG_CHOPCONF, chopconf)) return false;

    if (!verifyWrite(REG_TPOWERDOWN, config.tpowerdown)) return false;

    // TCOOLTHRS -- minimum velocity for StallGuard to be active
    // Set to a high value so StallGuard is always active
    if (!verifyWrite(REG_TCOOLTHRS, config.tcool_threshold)) return false;

    if (!verifyWrite(REG_SGTHRS, config.sg_threshold)) return false;

    return true;
}

uint16_t TMC2209::getStallGuardResult() {
    uint32_t result = 0;
    readRegister(REG_SG_RESULT, result);
    return static_cast<uint16_t>(result & 0x1FF);
}

void TMC2209::enable(void) {
    // Enable pin is active low -- handled by Stepper class
    // Here we just ensure TOFF != 0 in CHOPCONF
}

void TMC2209::disable(void) {
    // Set TOFF=0 in CHOPCONF to disable driver output
    uint32_t chopconf = 0;
    readRegister(REG_CHOPCONF, chopconf);
    chopconf &= ~0x0FUL;  // clear TOFF bits
    writeRegister(REG_CHOPCONF, chopconf);
}

TMC2209Config TMC2209::readConfig(void) {
	TMC2209Config config;

	uint32_t gconf = 0;
	if (readRegister(REG_GCONF, gconf)) {
		config.en_spreadcycle  = (gconf >> 2) & 0x01;
		config.pdn_disable       = (gconf >> 6) & 0x01;  // should always be 1
		config.mstep_reg_select  = (gconf >> 7) & 0x01;  // should always be 1
	}
	uint32_t ihold_irun = 0;
	if (readRegister(REG_IHOLD_IRUN, ihold_irun)) {
		config.hold_current  = (ihold_irun >> 0)  & 0x1F;  // bits 4:0
		config.run_current   = (ihold_irun >> 8)  & 0x1F;  // bits 12:8
		config.ihold_delay   = (ihold_irun >> 16) & 0x0F;  // bits 19:16
	}
	uint32_t chopconf = 0;
	if (readRegister(REG_CHOPCONF, chopconf)) {
	    uint8_t mres_bits = (chopconf >> 24) & 0x0F;  // extract bits 27:24
	    config.microsteps = bitsToMicrosteps(mres_bits);
	}
	uint32_t tcoolthrs = 0;
	readRegister(REG_TCOOLTHRS, tcoolthrs);
	config.tcool_threshold = tcoolthrs & 0xFFFFF;
	uint32_t sgthrs = 0;
	readRegister(REG_SGTHRS, sgthrs);
	config.sg_threshold = sgthrs & 0xFF;

	return config;
}

TMC2209::~TMC2209(void) = default;


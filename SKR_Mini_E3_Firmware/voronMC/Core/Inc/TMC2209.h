/*
 * TMS2209.h
 *
 *  Created on: 30 Mar 2026
 *      Author: f402n
 */

#ifndef SRC_TMC2209_H_
#define SRC_TMC2209_H_

// TMC2209.h
#pragma once
#include "Config.h"
#include "IHAL/IUART.h"
#include "IClass/ITMC2209.h"
#include <cstdint>


class TMC2209 : public ITMC2209 {
public:
    TMC2209(IUART& iuart, uint8_t slave_addr);
    void flushRx(void) override;
    bool init(const TMC2209Config& config) override;		// Initialise driver with sensible defaults
    uint16_t getStallGuardResult(void) override;			// StallGuard
    void enable(void) override;								// Enable/disable driver
    void disable(void) override;
    TMC2209Config readConfig(void) override;
    uint8_t calcCRC(uint8_t* data, uint8_t len) override;	// CRC
    bool isConnected(void) override;						// Read IFCNT register to verify comms are working
    virtual ~TMC2209(void) override;

private:
    IUART& iuart_;
    uint8_t slave_addr_;

    // Low level read/write
    void writeRegister(uint8_t reg, uint32_t data);
    bool verifyWrite(uint8_t reg, uint32_t data);
    bool readRegister(uint8_t reg, uint32_t& data);

    // Microstepping resolution to MRES bits
    uint8_t microstepsToBits(uint8_t microsteps);
    uint8_t bitsToMicrosteps(uint8_t bits);
};

#endif /* SRC_TMC2209_H_ */

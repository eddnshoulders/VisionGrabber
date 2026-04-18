/*
 * MockTMC2209Simple.h
 *
 *  Created on: 7 Apr 2026
 *      Author: f402n
 */

#ifndef MOCKS_MOCKTMC2209SIMPLE_H_
#define MOCKS_MOCKTMC2209SIMPLE_H_

#include "IClass/ITMC2209.h"

class MockTMC2209Simple : public ITMC2209 {
public:
    bool init(const TMC2209Config& config) override {
        init_called = true;
        last_config = config;
        return init_return_val;
    }

    void flushRx(void) override {}
    uint16_t getStallGuardResult(void) override { return 0; }
    void enable(void) override {}
    void disable(void) override {}
    TMC2209Config readConfig(void) override { return TMC2209Config{}; }
    uint8_t calcCRC(uint8_t* data, uint8_t len) override { return 0; }
    bool isConnected(void) override { return true; }

    bool init_called = false;
    bool init_return_val = true;  // control whether init succeeds
    TMC2209Config last_config;
};

#endif /* MOCKS_MOCKTMC2209SIMPLE_H_ */

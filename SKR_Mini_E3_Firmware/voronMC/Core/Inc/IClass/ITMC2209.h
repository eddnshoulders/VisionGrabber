/*
 * ITMC2209.h
 *
 *  Created on: 7 Apr 2026
 *      Author: f402n
 */

#ifndef SRC_ITMC2209_H_
#define SRC_ITMC2209_H_

#include <cstdint>

struct TMC2209Config {
    uint8_t  run_current      = 8;    	  // 0-31
    uint8_t  hold_current     = 2;        // 0-31
    uint8_t  microsteps       = 32;
    uint8_t  sg_threshold     = 100;      // stallgaurd threshold above which diag pin triggered (0-1023)
    uint8_t  ihold_delay      = 3;	      // ramp rate from irun to ihold after tpwrdown elapsed (0-15, 15 = slowest)
    uint8_t  tpowerdown	      = 20;	      // n x 2ms: time to start of ramp to hold current
    uint32_t tcool_threshold  = 0xFFFFF;  // 20bit value:
    bool     en_spreadcycle   = true;
    bool	 pdn_disable      = true;
    bool	 mstep_reg_select = true;
    bool	 sg_enable		  = true;
};


class ITMC2209 {
public:
	virtual void flushRx(void) = 0;
	virtual bool init(const TMC2209Config& config) = 0;			// Initialise driver with sensible defaults
	virtual uint16_t getStallGuardResult(void) = 0;				// StallGuard
	virtual void enable(void) = 0;								// Enable/disable driver
	virtual void disable(void) = 0;
	virtual TMC2209Config readConfig(void) = 0;
	virtual uint8_t calcCRC(uint8_t* data, uint8_t len) = 0;	// CRC
	virtual bool isConnected(void) = 0;		    				// Read IFCNT register to verify comms are working

    virtual ~ITMC2209(void) = default;
};

#endif /* SRC_ITMC2209_H_ */

/*
 * MockUART.h
 *
 *  Created on: 3 Apr 2026
 *      Author: f402n
 */

#ifndef MOCKS_MOCKGPIO_H_
#define MOCKS_MOCKGPIO_H_

#include "IHAL/IGPIO.h"

class MockGPIO : public IGPIO {
public:
	void setPin(void) override { pinSt = true; }
	void resetPin(void) override { pinSt = false; };
	bool readPin(void) override { return pinSt; }
	void togglePin(void) override { pinSt ? pinSt = false : pinSt = true; }
	IGPIO_StatusTypeDef lockPin() override { return IGPIO_OK; }

	bool pinSt = false;
	IGPIO_StatusTypeDef pinLocked = IGPIO_ERROR;
};

#endif /* MOCKS_MOCKGPIO_H_ */

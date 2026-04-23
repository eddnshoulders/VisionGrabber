/*
 * MockSYS.h
 *
 *  Created on: 5 Apr 2026
 *      Author: f402n
 */

#ifndef MOCKS_MOCKSYS_H_
#define MOCKS_MOCKSYS_H_

#include <IHAL/ISYS.h>

class MockSYS : public ISYS {
public:
	void NOP(void) override { NOP_calls++; }

	uint32_t NOP_calls = 0;
};

#endif /* MOCKS_MOCKSYS_H_ */

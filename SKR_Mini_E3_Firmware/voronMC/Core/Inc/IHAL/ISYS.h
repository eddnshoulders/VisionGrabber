/*
 * ISYS.h
 *
 *  Created on: 5 Apr 2026
 *      Author: f402n
 */

#ifndef SRC_ISYS_H_
#define SRC_ISYS_H_

#include <cstdint>

class ISYS {
public:
	virtual void NOP(void) = 0;

	virtual ~ISYS(void) = default;
};

#endif /* SRC_ISYS_H_ */

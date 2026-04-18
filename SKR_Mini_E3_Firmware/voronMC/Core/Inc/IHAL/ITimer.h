/*
 * ITimer.h
 *
 *  Created on: 3 Apr 2026
 *      Author: f402n
 */

#ifndef SRC_ITIMER_H_
#define SRC_ITIMER_H_

#include <cstdint>

class ITimer {
public:
	virtual void Start_PWM(void) = 0;
	virtual void Stop_PWM(void) = 0;
	virtual void Start_IT(void) = 0;
	virtual void Stop_IT(void) = 0;
	virtual void writeCompareReg(uint32_t value) = 0;
	virtual void setARRPeriod(uint32_t period) = 0;
	virtual void setCounter(uint32_t count) = 0;

	virtual ~ITimer(void) = default;
};

#endif /* SRC_ITIMER_H_ */
